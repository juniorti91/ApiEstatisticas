from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.fixture import Fixture
from app.models.odds_history import OddsHistoryPoint
from app.models.recommendation import Recommendation, RecommendationStatus
from app.schemas.odds_history import OddsHistoryPointOut
from app.schemas.recommendation import RecommendationOut

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/fixture/{fixture_id}", response_model=list[RecommendationOut])
async def list_fixture_recommendations(fixture_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Recommendation)
        .where(Recommendation.fixture_id == fixture_id)
        .order_by(Recommendation.is_primary.desc(), Recommendation.expected_value.desc())
    )
    return result.scalars().all()


@router.get("/{recommendation_id}/odds-history", response_model=list[OddsHistoryPointOut])
async def get_odds_history(recommendation_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(OddsHistoryPoint)
        .where(OddsHistoryPoint.recommendation_id == recommendation_id)
        .order_by(OddsHistoryPoint.minute)
    )
    return result.scalars().all()


@router.get("/pending", response_model=list[RecommendationOut])
async def list_pending_recommendations(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Recommendation)
        .join(Fixture, Fixture.id == Recommendation.fixture_id)
        .where(Recommendation.status == RecommendationStatus.PENDING.value)
        .order_by(Recommendation.expected_value.desc())
    )
    return result.scalars().all()
