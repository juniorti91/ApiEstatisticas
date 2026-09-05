from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.fixture import Fixture
from app.models.recommendation import Recommendation
from app.schemas.recommendation import RecommendationHistoryRow

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/recommendations", response_model=list[RecommendationHistoryRow])
async def recommendation_history(
    limit: int = Query(50, ge=1, le=200), session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Recommendation).order_by(Recommendation.created_at.desc()).limit(limit)
    )
    recs = list(result.scalars().all())

    rows: list[RecommendationHistoryRow] = []
    for rec in recs:
        fixture = await session.get(
            Fixture, rec.fixture_id, options=[selectinload(Fixture.home_team), selectinload(Fixture.away_team)]
        )
        if fixture is None:
            continue
        label = f"{fixture.home_team.name} x {fixture.away_team.name}"
        result_score = f"{fixture.goals_home}-{fixture.goals_away}" if fixture.status in ("FT", "AET", "PEN") else None
        rows.append(
            RecommendationHistoryRow(
                id=rec.id,
                fixture_label=label,
                played_on=fixture.kickoff_at,
                selection=f"{rec.team_focus} - {rec.selection}".strip(" -") if rec.team_focus else rec.selection,
                odd=rec.odd,
                status=rec.status,
                result_score=result_score,
            )
        )
    return rows
