"""
Cache do historico recente de jogos de um time (adversario, mando de
campo, competicao, placar e placar do intervalo) - usado pela tela
"Comparativo Histórico" (forma dos times).

Pega o MAXIMO de jogos que os filtros do frontend podem precisar
(MAX_HISTORY_GAMES) numa unica chamada a API (mesmo endpoint
`team_last_fixtures` que team_form_service.py ja usa para calcular a
"forma"), e guarda uma linha por jogo em vez de so as medias - assim os
filtros de "quantos jogos", "so em casa/fora" e "so na mesma competicao"
sao recalculados INSTANTANEAMENTE no frontend, sem nenhuma chamada nova a
API a cada mudanca de filtro.

NAO busca estatisticas detalhadas (chutes, escanteios etc) de cada jogo
passado - isso custaria uma chamada de API extra POR JOGO (como
team_form_service.py ja faz, so que la a amostra e bem menor, 3-5 jogos).
Aqui so precisamos de gols e placar do intervalo, que ja vem de graca na
propria lista de jogos.

Tambem NAO busca odds pre-jogo de cada partida passada (minima/media/
maxima) - isso custaria uma chamada extra POR JOGO POR TIME a cada
refresh, e a cobertura pode ter buracos parecidos com os ja vistos nas
odds ao vivo (ver o bug do "Mais de 3.5 Gols" investigado antes nesse
projeto). Fica como proxima etapa, so se o usuario confirmar que quer
gastar a cota de API nisso.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from app.models.team_match_history import TeamMatchHistory
from app.services.api_football_client import ApiFootballError, api_football_client

logger = logging.getLogger("betanalyzer.team_history")

# Teto alto o suficiente para cobrir o maior filtro que a tela permite
# (ver WINDOWS/games slider no frontend) - refeito numa unica chamada por
# time a cada refresh, nao uma chamada por filtro.
MAX_HISTORY_GAMES = 20
CACHE_MAX_AGE_HOURS = 12


def _extract_row(team: Team, raw_fixture: dict) -> TeamMatchHistory | None:
    fixture = raw_fixture.get("fixture") or {}
    fixture_api_id = fixture.get("id")
    if fixture_api_id is None:
        return None

    home = raw_fixture.get("teams", {}).get("home") or {}
    away = raw_fixture.get("teams", {}).get("away") or {}
    is_home = home.get("id") == team.api_id
    opponent = away if is_home else home

    goals = raw_fixture.get("goals") or {}
    goals_home = goals.get("home") or 0
    goals_away = goals.get("away") or 0
    goals_for = goals_home if is_home else goals_away
    goals_against = goals_away if is_home else goals_home

    # score.halftime pode vir ausente (None) em jogos antigos/ligas
    # menores - tratamos como "sem dado" em vez de assumir 0 x 0, que
    # inventaria um resultado de intervalo que pode nao ter acontecido.
    halftime = (raw_fixture.get("score") or {}).get("halftime") or {}
    ht_home = halftime.get("home")
    ht_away = halftime.get("away")
    if ht_home is None or ht_away is None:
        ht_goals_for = None
        ht_goals_against = None
    else:
        ht_goals_for = ht_home if is_home else ht_away
        ht_goals_against = ht_away if is_home else ht_home

    league = raw_fixture.get("league") or {}
    played_at_raw = fixture.get("date")
    try:
        # API-Football manda ISO com offset (ex: "2026-09-05T22:30:00+00:00") -
        # convertido pra naive UTC pra ficar no mesmo padrao naive do resto
        # do banco (ver comentario sobre datetime.utcnow() em outros models).
        played_at = datetime.fromisoformat(played_at_raw).replace(tzinfo=None) if played_at_raw else datetime.utcnow()
    except ValueError:
        played_at = datetime.utcnow()

    return TeamMatchHistory(
        team_id=team.id,
        fixture_api_id=fixture_api_id,
        opponent_name=opponent.get("name") or "?",
        is_home=is_home,
        league_api_id=league.get("id") or 0,
        league_name=league.get("name") or "",
        played_at=played_at,
        goals_for=goals_for,
        goals_against=goals_against,
        ht_goals_for=ht_goals_for,
        ht_goals_against=ht_goals_against,
    )


async def get_or_refresh_team_history(
    session: AsyncSession, team: Team, max_age_hours: int = CACHE_MAX_AGE_HOURS
) -> list[TeamMatchHistory]:
    """Retorna o historico cacheado (mais recente primeiro), buscando de
    novo na API-Football quando o cache esta ausente ou mais velho que
    `max_age_hours` (mesma politica de TeamForm)."""
    result = await session.execute(
        select(TeamMatchHistory)
        .where(TeamMatchHistory.team_id == team.id)
        .order_by(TeamMatchHistory.played_at.desc())
    )
    cached = list(result.scalars().all())

    is_stale = not cached or (datetime.utcnow() - cached[0].fetched_at) > timedelta(hours=max_age_hours)
    if not is_stale:
        return cached

    try:
        recent = await api_football_client.team_last_fixtures(team.api_id, last=MAX_HISTORY_GAMES)
    except ApiFootballError as exc:
        logger.warning("Falha ao buscar historico do time %s: %s", team.name, exc)
        return cached  # usa cache antigo (mesmo vencido) em vez de falhar pro usuario

    fetched_at = datetime.utcnow()
    rows: list[TeamMatchHistory] = []
    for raw_fixture in recent:
        row = _extract_row(team, raw_fixture)
        if row is not None:
            row.fetched_at = fetched_at
            rows.append(row)

    if not rows:
        return cached  # API nao devolveu nada de aproveitavel - mantem o cache anterior

    # Recria do zero: mais simples que upsert por jogo, e a tabela e
    # pequena o bastante (no maximo MAX_HISTORY_GAMES linhas por time).
    await session.execute(delete(TeamMatchHistory).where(TeamMatchHistory.team_id == team.id))
    session.add_all(rows)
    await session.commit()

    rows.sort(key=lambda r: r.played_at, reverse=True)
    return rows
