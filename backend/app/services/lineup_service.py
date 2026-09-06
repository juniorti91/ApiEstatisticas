"""
Busca e cacheia escalacao provavel/titular, tecnicos, arbitro e lesoes de
uma partida - usado pela tela "Escalações".

Chama 3 endpoints da API-Football (lineups, o fixture basico so pelo campo
`referee`, e injuries) SOB DEMANDA - so quando o usuario abre essa tela
pra uma partida especifica, nunca no ciclo automatico de coleta (isso
custaria 2-3 chamadas extras por partida monitorada a cada 5 minutos, sem
necessidade nenhuma: escalacao e arbitro nao mudam durante o jogo).

Cacheado com validade de horas (CACHE_MAX_AGE_HOURS) porque, ao contrario
de estatisticas ao vivo, essa informacao e publicada pela API-Football
umas ~1h antes do apito inicial e nao muda mais depois disso - reconsultar
a cada poll da tela seria desperdicio de cota.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fixture import Fixture
from app.models.lineup_cache import FixtureLineupCache
from app.models.team import Team
from app.services.api_football_client import ApiFootballError, api_football_client

logger = logging.getLogger("betanalyzer.lineups")

CACHE_MAX_AGE_HOURS = 6


def _parse_team_lineup(raw_team_entry: dict) -> dict:
    def parse_player_list(key: str) -> list[dict]:
        out = []
        for item in raw_team_entry.get(key, []) or []:
            player = item.get("player") or {}
            out.append(
                {
                    "number": player.get("number"),
                    "name": player.get("name") or "?",
                    "pos": player.get("pos") or "",
                    # "linha:posicao" (ex: "2:3") - None quando a API nao
                    # informou (comum em reservas, que nao tem posicao em
                    # campo ainda). Ver Lineups.jsx pra como isso vira layout.
                    "grid": player.get("grid"),
                }
            )
        return out

    coach = raw_team_entry.get("coach") or {}
    return {
        "formation": raw_team_entry.get("formation"),
        "coach": coach.get("name"),
        "startXI": parse_player_list("startXI"),
        "substitutes": parse_player_list("substitutes"),
    }


def _parse_injuries(raw_injuries: list[dict], home_api_id: int, away_api_id: int) -> tuple[list[dict], list[dict]]:
    home: list[dict] = []
    away: list[dict] = []
    for entry in raw_injuries:
        team_id = (entry.get("team") or {}).get("id")
        player = entry.get("player") or {}
        row = {
            "player_name": player.get("name") or "?",
            "reason": player.get("reason") or entry.get("type") or "Motivo não informado",
            "type": entry.get("type") or "",
        }
        if team_id == home_api_id:
            home.append(row)
        elif team_id == away_api_id:
            away.append(row)
    return home, away


async def get_or_refresh_lineup(
    session: AsyncSession, fixture: Fixture, max_age_hours: int = CACHE_MAX_AGE_HOURS
) -> FixtureLineupCache | None:
    result = await session.execute(
        select(FixtureLineupCache).where(FixtureLineupCache.fixture_id == fixture.id)
    )
    cached = result.scalar_one_or_none()

    is_stale = cached is None or (datetime.utcnow() - cached.fetched_at) > timedelta(hours=max_age_hours)
    if not is_stale:
        return cached

    try:
        raw_lineups = await api_football_client.fixture_lineups(fixture.api_fixture_id)
    except ApiFootballError as exc:
        logger.warning("Falha ao buscar escalacao da partida %s: %s", fixture.api_fixture_id, exc)
        return cached  # cache antigo (ou None) em vez de quebrar a tela

    home_team = await session.get(Team, fixture.home_team_id)
    away_team = await session.get(Team, fixture.away_team_id)

    home_parsed: dict = {}
    away_parsed: dict = {}
    for entry in raw_lineups:
        team_id = (entry.get("team") or {}).get("id")
        if team_id == home_team.api_id:
            home_parsed = _parse_team_lineup(entry)
        elif team_id == away_team.api_id:
            away_parsed = _parse_team_lineup(entry)

    # Escalacao ainda nao publicada pela API (comum ate ~1h antes do apito
    # inicial) - se ja tinhamos um cache (de uma tentativa anterior ou de
    # quando a escalacao ja tinha saido), mantem ele em vez de sobrescrever
    # com listas vazias. Quando NAO ha cache nenhum ainda, segue em frente
    # pra ao menos tentar buscar arbitro/lesoes (que costumam sair antes da
    # escalacao) - melhor mostrar isso na tela do que nada, e o
    # fetched_at gravado no final evita martelar a API de novo antes de
    # max_age_hours passar.
    if not home_parsed.get("startXI") and not away_parsed.get("startXI") and cached is not None:
        return cached

    referee: str | None = None
    try:
        raw_fixture = await api_football_client.fixture_by_id(fixture.api_fixture_id)
        if raw_fixture:
            referee = (raw_fixture.get("fixture") or {}).get("referee")
    except ApiFootballError as exc:
        logger.info("Falha ao buscar arbitro da partida %s: %s", fixture.api_fixture_id, exc)

    injuries_home: list[dict] = []
    injuries_away: list[dict] = []
    try:
        raw_injuries = await api_football_client.fixture_injuries(fixture.api_fixture_id)
        injuries_home, injuries_away = _parse_injuries(raw_injuries, home_team.api_id, away_team.api_id)
    except ApiFootballError as exc:
        # Endpoint separado, cobertura variavel por liga/plano - lista
        # vazia e o comportamento normal aqui, nao um erro pro usuario.
        logger.info("Lesoes/suspensoes indisponiveis para a partida %s: %s", fixture.api_fixture_id, exc)

    if cached is None:
        cached = FixtureLineupCache(fixture_id=fixture.id)
        session.add(cached)

    cached.fetched_at = datetime.utcnow()
    cached.referee = referee
    cached.formation_home = home_parsed.get("formation")
    cached.formation_away = away_parsed.get("formation")
    cached.coach_home = home_parsed.get("coach")
    cached.coach_away = away_parsed.get("coach")
    cached.lineup_home = home_parsed.get("startXI") or []
    cached.lineup_away = away_parsed.get("startXI") or []
    cached.substitutes_home = home_parsed.get("substitutes") or []
    cached.substitutes_away = away_parsed.get("substitutes") or []
    cached.injuries_home = injuries_home
    cached.injuries_away = injuries_away

    await session.commit()
    await session.refresh(cached)
    return cached
