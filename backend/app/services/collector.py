"""
Coletor de dados das partidas ao vivo.

Dois ritmos, por performance:
  * `scan_live_fixtures`  - roda com mais frequencia (padrao 2 min) e e
    barato: so lista partidas ao vivo nas ligas monitoradas e
    cria/atualiza os registros de Fixture. E o que decide QUAIS partidas
    entram em observacao.
  * `collect_snapshots`   - roda a cada 5 minutos (o requisito principal)
    e busca as estatisticas detalhadas (escanteios, chutes, posse...) de
    cada partida ja em observacao, gravando um MatchSnapshot por partida.

Ambos sao chamados pelo scheduler (app/services/scheduler.py).
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.fixture import Fixture
from app.models.league import League
from app.models.snapshot import MatchSnapshot
from app.models.team import Team
from app.services.api_football_client import ApiFootballError, api_football_client
from app.services.stats_mapper import parse_fixture_statistics

logger = logging.getLogger("betanalyzer.collector")

FINISHED_STATUSES = {"FT", "AET", "PEN"}
LIVE_STATUSES = {"1H", "2H", "HT", "ET", "BT", "P", "LIVE"}


async def _get_or_create_league(session: AsyncSession, raw_league: dict) -> League:
    api_id = raw_league["id"]
    result = await session.execute(select(League).where(League.api_id == api_id))
    league = result.scalar_one_or_none()
    if league is None:
        league = League(
            api_id=api_id,
            name=raw_league.get("name", ""),
            country=raw_league.get("country", ""),
            logo_url=raw_league.get("logo", ""),
            season=raw_league.get("season", 0),
        )
        session.add(league)
        await session.flush()
    return league


async def _get_or_create_team(session: AsyncSession, raw_team: dict) -> Team:
    api_id = raw_team["id"]
    result = await session.execute(select(Team).where(Team.api_id == api_id))
    team = result.scalar_one_or_none()
    if team is None:
        team = Team(api_id=api_id, name=raw_team.get("name", ""), logo_url=raw_team.get("logo", ""))
        session.add(team)
        await session.flush()
    return team


async def _upsert_fixture(session: AsyncSession, raw_fixture: dict) -> Fixture:
    fx = raw_fixture["fixture"]
    league_data = raw_fixture["league"]
    teams_data = raw_fixture["teams"]
    goals_data = raw_fixture.get("goals", {})

    league = await _get_or_create_league(session, league_data)
    home_team = await _get_or_create_team(session, teams_data["home"])
    away_team = await _get_or_create_team(session, teams_data["away"])

    result = await session.execute(
        select(Fixture).where(Fixture.api_fixture_id == fx["id"])
    )
    fixture = result.scalar_one_or_none()
    status_short = fx.get("status", {}).get("short", "NS")
    elapsed = fx.get("status", {}).get("elapsed") or 0

    if fixture is None:
        fixture = Fixture(
            api_fixture_id=fx["id"],
            league_id=league.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            round=league_data.get("round", ""),
            kickoff_at=datetime.fromisoformat(fx["date"].replace("Z", "+00:00")).replace(tzinfo=None),
            status=status_short,
            elapsed_minutes=elapsed,
            goals_home=goals_data.get("home") or 0,
            goals_away=goals_data.get("away") or 0,
            is_monitored=status_short in LIVE_STATUSES,
        )
        session.add(fixture)
        await session.flush()
    else:
        fixture.status = status_short
        fixture.elapsed_minutes = elapsed
        fixture.goals_home = goals_data.get("home") or 0
        fixture.goals_away = goals_data.get("away") or 0
        if status_short in LIVE_STATUSES:
            fixture.is_monitored = True

    return fixture


async def scan_live_fixtures(session: AsyncSession) -> list[Fixture]:
    """
    Descobre partidas ao vivo nas ligas monitoradas e as coloca em
    observacao, respeitando `settings.max_monitored_fixtures` - protege a
    cota da API quando MONITORED_LEAGUE_IDS esta vazio (todas as ligas do
    mundo) e aparecem muitas partidas de uma vez. Partidas que ja estavam
    em observacao continuam sendo atualizadas normalmente ate terminarem,
    mesmo que o numero total passe do limite; o limite so impede que
    NOVAS partidas entrem quando ja estamos no teto.
    """
    try:
        raw_fixtures = await api_football_client.live_fixtures(settings.monitored_league_id_list)
    except ApiFootballError as exc:
        logger.warning("Falha ao escanear partidas ao vivo: %s", exc)
        return []

    result = await session.execute(select(Fixture).where(Fixture.is_monitored.is_(True)))
    monitored_fixtures = list(result.scalars().all())
    already_monitored_ids = {f.api_fixture_id for f in monitored_fixtures}
    still_live_ids = {raw["fixture"]["id"] for raw in raw_fixtures}
    max_fixtures = settings.max_monitored_fixtures

    tracked: list[Fixture] = []
    new_slots_used = 0
    skipped = 0

    for raw in raw_fixtures:
        api_fixture_id = raw["fixture"]["id"]
        if api_fixture_id not in already_monitored_ids:
            remaining = max_fixtures - (len(already_monitored_ids) + new_slots_used)
            if remaining <= 0:
                skipped += 1
                continue
            new_slots_used += 1
        fixture = await _upsert_fixture(session, raw)
        tracked.append(fixture)

    # Partidas que estavam em observacao mas sumiram da lista "ao vivo
    # agora" provavelmente terminaram (ou foram interrompidas/adiadas).
    # Confirma o estado final com UMA chamada pontual so para essas -
    # normalmente 0 a 2 por ciclo - em vez do collect_snapshots reconsultar
    # TODAS as partidas monitoradas a cada 5 minutos so pra saber se ainda
    # estao ao vivo (o que gastava 1 requisicao extra por partida
    # monitorada a cada coleta, sem necessidade: o status/minuto/placar
    # normal ja vem de graca deste mesmo escaneamento a cada 2 minutos).
    dropped = [
        f for f in monitored_fixtures
        if f.api_fixture_id not in still_live_ids and f.status in LIVE_STATUSES
    ]
    for fixture in dropped:
        try:
            raw_fixture = await api_football_client.fixture_by_id(fixture.api_fixture_id)
        except ApiFootballError as exc:
            logger.warning("Falha ao confirmar encerramento da partida %s: %s", fixture.api_fixture_id, exc)
            continue
        if raw_fixture is None:
            continue
        fx_status = raw_fixture["fixture"]["status"]
        fixture.status = fx_status.get("short", fixture.status)
        fixture.elapsed_minutes = fx_status.get("elapsed") or fixture.elapsed_minutes
        fixture.goals_home = raw_fixture.get("goals", {}).get("home") or 0
        fixture.goals_away = raw_fixture.get("goals", {}).get("away") or 0

    await session.commit()
    if skipped:
        logger.info(
            "Scan: limite de %d partidas monitoradas simultaneamente atingido - "
            "%d partida(s) ao vivo ignorada(s) para poupar cota da API.",
            max_fixtures, skipped,
        )
    if dropped:
        logger.info("Scan: %d partida(s) sairam da lista ao vivo - status final confirmado.", len(dropped))
    logger.info("Scan concluido: %d partida(s) ao vivo em observacao.", len(tracked))
    return tracked


async def track_fixture_by_id(session: AsyncSession, api_fixture_id: int) -> Fixture | None:
    """Adiciona manualmente uma partida especifica a observacao, mesmo que
    fora das ligas monitoradas automaticamente (usado pelo endpoint
    POST /api/matches/track)."""
    try:
        raw_fixture = await api_football_client.fixture_by_id(api_fixture_id)
    except ApiFootballError as exc:
        logger.warning("Falha ao buscar partida %s para monitoramento manual: %s", api_fixture_id, exc)
        return None
    if raw_fixture is None:
        return None

    fixture = await _upsert_fixture(session, raw_fixture)
    fixture.is_monitored = True
    await session.commit()
    await session.refresh(fixture)
    return fixture


async def collect_snapshots(session: AsyncSession) -> int:
    """
    Para cada partida em observacao e efetivamente ao vivo, busca as
    estatisticas atuais na API e grava um MatchSnapshot. Retorna quantos
    snapshots foram criados.

    NAO rebusca status/minuto/placar aqui: isso ja vem fresco (no maximo
    ~2 minutos desatualizado) do `scan_live_fixtures`, que roda mais
    seguido e ja atualiza esses campos em `Fixture` para toda partida ao
    vivo (e confirma o encerramento das que sumiram da lista). Refazer
    essa consulta por partida a cada 5 minutos so pra reler o mesmo dado
    era 1 requisicao inteira desperdicada por partida monitorada a cada
    coleta - com 15 partidas isso sozinho respondia por boa parte do
    consumo de cota.
    """
    result = await session.execute(
        select(Fixture).where(Fixture.is_monitored.is_(True))
    )
    fixtures = list(result.scalars().all())
    created = 0

    for fixture in fixtures:
        if fixture.status in FINISHED_STATUSES:
            # Nao coleta snapshot de jogo encerrado; o results_tracker cuida dele.
            continue
        if fixture.status not in LIVE_STATUSES:
            continue

        try:
            raw_stats = await api_football_client.fixture_statistics(fixture.api_fixture_id)
        except ApiFootballError as exc:
            logger.warning("Falha ao buscar estatisticas da partida %s: %s", fixture.api_fixture_id, exc)
            continue

        home_team = await session.get(Team, fixture.home_team_id)
        away_team = await session.get(Team, fixture.away_team_id)
        parsed = parse_fixture_statistics(raw_stats, home_team.api_id, away_team.api_id)

        snapshot = MatchSnapshot(
            fixture_id=fixture.id,
            captured_at=datetime.utcnow(),
            minute=fixture.elapsed_minutes,
            goals_home=fixture.goals_home,
            goals_away=fixture.goals_away,
            **parsed,
        )
        session.add(snapshot)
        created += 1

    await session.commit()
    logger.info("Coleta concluida: %d snapshot(s) gravado(s).", created)
    return created
