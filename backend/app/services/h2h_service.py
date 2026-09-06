"""
Busca e cacheia os ultimos confrontos diretos (H2H) entre os dois times de
uma partida - usado pelo card "H2H pre-jogo".

So 1 chamada a API-Football por PAR de times (nao por partida) - se os
mesmos dois times aparecerem em partidas monitoradas diferentes (raro, mas
possivel em torneios de ida e volta), o cache e reaproveitado.

Cacheado com validade de horas (CACHE_MAX_AGE_HOURS): o historico entre
dois times so muda quando eles jogam de novo um contra o outro, o que
normalmente leva semanas - bem diferente da cadencia dos snapshots ao vivo.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.head_to_head_cache import HeadToHeadCache
from app.models.team import Team
from app.services.api_football_client import ApiFootballError, api_football_client

logger = logging.getLogger("betanalyzer.h2h")

CACHE_MAX_AGE_HOURS = 12
# Quantos jogos passados pedir a API por chamada (guardamos todos, o
# endpoint so devolve os N ultimos ja ordenados do mais recente pro mais
# antigo) - a tela mostra so os 5 mais recentes (ver matches.py).
FETCH_LAST = 10


def _pair_key(team_a_id: int, team_b_id: int) -> tuple[int, int]:
    """Chave canonica do par, independente de qual time e casa/fora na
    partida atual - assim "Time X x Time Y" e "Time Y x Time X" reusam o
    mesmo cache."""
    return (team_a_id, team_b_id) if team_a_id <= team_b_id else (team_b_id, team_a_id)


def _extract_row(raw_fixture: dict) -> dict | None:
    fixture = raw_fixture.get("fixture") or {}
    fixture_api_id = fixture.get("id")
    if fixture_api_id is None:
        return None

    league = raw_fixture.get("league") or {}
    teams = raw_fixture.get("teams") or {}
    goals = raw_fixture.get("goals") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}

    date_raw = fixture.get("date")
    try:
        # Mesma conversao ISO-com-offset -> naive UTC usada em
        # team_history_service.py, pra ficar no mesmo padrao do resto do banco.
        played_at = datetime.fromisoformat(date_raw).replace(tzinfo=None) if date_raw else None
    except ValueError:
        played_at = None

    return {
        "fixture_api_id": fixture_api_id,
        "date": played_at.isoformat() if played_at else None,
        "league_name": league.get("name") or "",
        "home_name": home.get("name") or "?",
        "away_name": away.get("name") or "?",
        "home_goals": goals.get("home"),
        "away_goals": goals.get("away"),
    }


async def get_or_refresh_h2h(
    session: AsyncSession, home_team: Team, away_team: Team, max_age_hours: int = CACHE_MAX_AGE_HOURS
) -> HeadToHeadCache | None:
    a_id, b_id = _pair_key(home_team.id, away_team.id)
    result = await session.execute(
        select(HeadToHeadCache).where(
            HeadToHeadCache.team_a_id == a_id, HeadToHeadCache.team_b_id == b_id
        )
    )
    cached = result.scalar_one_or_none()

    is_stale = cached is None or (datetime.utcnow() - cached.fetched_at) > timedelta(hours=max_age_hours)
    if not is_stale:
        return cached

    try:
        raw = await api_football_client.head_to_head(home_team.api_id, away_team.api_id, last=FETCH_LAST)
    except ApiFootballError as exc:
        logger.warning(
            "Falha ao buscar H2H entre %s e %s: %s", home_team.name, away_team.name, exc
        )
        return cached  # cache antigo (ou None) em vez de quebrar a tela

    rows = [row for row in (_extract_row(r) for r in raw) if row is not None]
    # A API ja costuma devolver do mais recente pro mais antigo, mas
    # garante isso explicitamente (data pode vir None em algum item raro).
    rows.sort(key=lambda r: r["date"] or "", reverse=True)

    if not rows and cached is not None:
        return cached  # API nao devolveu nada de aproveitavel - mantem cache anterior

    if cached is None:
        cached = HeadToHeadCache(team_a_id=a_id, team_b_id=b_id)
        session.add(cached)

    cached.matches = rows
    cached.fetched_at = datetime.utcnow()

    await session.commit()
    await session.refresh(cached)
    return cached
