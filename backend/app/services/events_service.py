"""
Busca e cacheia os eventos (gols, cartoes, substituicoes, VAR) de uma
partida - usado pela linha do tempo de eventos ("momentum") na aba Eventos.

Ao contrario da escalacao/arbitro (publicados uma vez, nunca mudam depois)
ou do historico de confrontos (so muda quando os times jogam de novo),
eventos acontecem AO VIVO durante a partida - por isso a validade do cache
e curta (CACHE_MAX_AGE_SECONDS_LIVE) enquanto o jogo esta em andamento, e
so passa a ser tratada como estavel (CACHE_MAX_AGE_HOURS_SETTLED, bem
maior) quando o status da partida nao e mais "ao vivo" - nesse caso os
eventos ja aconteceram todos e nao vao mudar mais.

Chamado SOB DEMANDA (quando o usuario abre a aba Eventos de uma partida),
nunca pelo ciclo automatico de coleta - mesmo padrao de lineup_service.py.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fixture import Fixture
from app.models.fixture_events_cache import FixtureEventsCache
from app.models.team import Team
from app.services.api_football_client import ApiFootballError, api_football_client

logger = logging.getLogger("betanalyzer.events")

# Mesma lista de status "ao vivo" usada em app/routers/matches.py e
# app/services/collector.py (o projeto repete essa constante pequena em
# cada arquivo que precisa dela, em vez de um modulo de constantes global).
LIVE_STATUSES = {"1H", "2H", "HT", "ET", "BT", "P", "LIVE"}

CACHE_MAX_AGE_SECONDS_LIVE = 60
CACHE_MAX_AGE_HOURS_SETTLED = 6


def _parse_events(raw_events: list[dict], home_api_id: int, away_api_id: int) -> list[dict]:
    out: list[dict] = []
    for entry in raw_events:
        time = entry.get("time") or {}
        team_id = (entry.get("team") or {}).get("id")
        player = entry.get("player") or {}
        assist = entry.get("assist") or {}
        minute = time.get("elapsed")
        if minute is None or team_id not in (home_api_id, away_api_id):
            continue  # evento sem minuto ou de time nao reconhecido - nao plota
        out.append(
            {
                "minute": minute,
                "extra_minute": time.get("extra"),
                "side": "home" if team_id == home_api_id else "away",
                "type": entry.get("type") or "",
                "detail": entry.get("detail") or "",
                "player_name": player.get("name"),
                "assist_name": assist.get("name"),
            }
        )
    out.sort(key=lambda e: (e["minute"], e["extra_minute"] or 0))
    return out


async def get_or_refresh_events(session: AsyncSession, fixture: Fixture) -> FixtureEventsCache | None:
    result = await session.execute(
        select(FixtureEventsCache).where(FixtureEventsCache.fixture_id == fixture.id)
    )
    cached = result.scalar_one_or_none()

    if fixture.status in LIVE_STATUSES:
        max_age = timedelta(seconds=CACHE_MAX_AGE_SECONDS_LIVE)
    else:
        max_age = timedelta(hours=CACHE_MAX_AGE_HOURS_SETTLED)

    is_stale = cached is None or (datetime.utcnow() - cached.fetched_at) > max_age
    if not is_stale:
        return cached

    try:
        raw_events = await api_football_client.fixture_events(fixture.api_fixture_id)
    except ApiFootballError as exc:
        logger.warning("Falha ao buscar eventos da partida %s: %s", fixture.api_fixture_id, exc)
        return cached  # cache antigo (ou None) em vez de quebrar a tela

    home_team = await session.get(Team, fixture.home_team_id)
    away_team = await session.get(Team, fixture.away_team_id)
    events = _parse_events(raw_events, home_team.api_id, away_team.api_id)

    if cached is None:
        cached = FixtureEventsCache(fixture_id=fixture.id)
        session.add(cached)

    cached.events = events
    cached.fetched_at = datetime.utcnow()

    await session.commit()
    await session.refresh(cached)
    return cached
