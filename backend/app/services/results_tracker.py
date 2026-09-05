"""
Ao final da partida, avalia cada recomendacao pendente contra o
resultado real e grava se foi acerto (win) ou erro (loss) - a peca que
fecha o ciclo pedido: sugerir -> registrar -> conferir.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fixture import Fixture
from app.models.recommendation import Recommendation, RecommendationStatus
from app.models.snapshot import MatchSnapshot
from app.models.team import Team
from app.services.api_football_client import ApiFootballError, api_football_client
from app.services.stats_mapper import parse_fixture_statistics

logger = logging.getLogger("betanalyzer.results_tracker")

FINISHED_STATUSES = {"FT", "AET", "PEN"}


async def _final_stats(session: AsyncSession, fixture: Fixture) -> dict[str, float]:
    """Tenta buscar as estatisticas finais frescas na API; se falhar, usa
    o ultimo snapshot gravado como aproximacao."""
    home_team = await session.get(Team, fixture.home_team_id)
    away_team = await session.get(Team, fixture.away_team_id)

    try:
        raw_stats = await api_football_client.fixture_statistics(fixture.api_fixture_id)
        if raw_stats:
            return parse_fixture_statistics(raw_stats, home_team.api_id, away_team.api_id)
    except ApiFootballError as exc:
        logger.warning("Nao foi possivel obter estatisticas finais de %s: %s", fixture.api_fixture_id, exc)

    result = await session.execute(
        select(MatchSnapshot)
        .where(MatchSnapshot.fixture_id == fixture.id)
        .order_by(MatchSnapshot.minute.desc())
        .limit(1)
    )
    last = result.scalars().first()
    if last is None:
        return {}
    return {
        "corners_home": last.corners_home,
        "corners_away": last.corners_away,
        "shots_on_target_home": last.shots_on_target_home,
        "shots_on_target_away": last.shots_on_target_away,
    }


def _settle_one(rec: Recommendation, fixture: Fixture, final_stats: dict[str, float], home_name: str, away_name: str) -> None:
    final_value: float | None = None
    won: bool | None = None

    if rec.market == "corners_over":
        is_home_focus = rec.team_focus == home_name
        final_value = final_stats.get("corners_home" if is_home_focus else "corners_away")
        if final_value is not None:
            won = final_value > rec.line

    elif rec.market == "total_goals_over":
        final_value = fixture.goals_home + fixture.goals_away
        won = final_value > rec.line

    elif rec.market == "btts_no":
        both_scored = fixture.goals_home > 0 and fixture.goals_away > 0
        final_value = 1.0 if both_scored else 0.0
        won = not both_scored

    if won is None:
        rec.status = RecommendationStatus.VOID.value
    else:
        rec.status = RecommendationStatus.WIN.value if won else RecommendationStatus.LOSS.value
    rec.final_stat_value = final_value
    rec.settled_at = datetime.utcnow()


async def settle_finished_fixtures(session: AsyncSession) -> int:
    """Varre partidas monitoradas que ja terminaram e ainda nao foram
    conferidas, avalia as recomendacoes pendentes e fecha o ciclo."""
    result = await session.execute(
        select(Fixture).where(
            Fixture.is_monitored.is_(True),
            Fixture.results_settled.is_(False),
            Fixture.status.in_(list(FINISHED_STATUSES)),
        )
    )
    fixtures = list(result.scalars().all())
    settled_count = 0

    for fixture in fixtures:
        home = await session.get(Team, fixture.home_team_id)
        away = await session.get(Team, fixture.away_team_id)
        final_stats = await _final_stats(session, fixture)

        rec_result = await session.execute(
            select(Recommendation).where(
                Recommendation.fixture_id == fixture.id,
                Recommendation.status == RecommendationStatus.PENDING.value,
            )
        )
        recs = list(rec_result.scalars().all())
        for rec in recs:
            _settle_one(rec, fixture, final_stats, home.name, away.name)
            settled_count += 1

        fixture.results_settled = True
        fixture.is_monitored = False

    await session.commit()
    if settled_count:
        logger.info("Resultados conferidos: %d recomendacao(oes) em %d partida(s).", settled_count, len(fixtures))
    return settled_count
