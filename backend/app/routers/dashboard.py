from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.recommendation import Recommendation, RecommendationStatus
from app.schemas.dashboard import PerformanceSummary
from app.services.collector import collect_snapshots, scan_live_fixtures
from app.services.recommendation_engine import generate_recommendations_for_all_live
from app.services.results_tracker import settle_finished_fixtures

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

STAKE_BASE = 100.0  # unidade de stake usada so para expressar lucro/prejuizo e ROI


def _compute_summary(recs: list[Recommendation], value_bets_total: int, total_all: int) -> tuple[float, float, float, float]:
    settled = [r for r in recs if r.status in (RecommendationStatus.WIN.value, RecommendationStatus.LOSS.value)]
    if not settled:
        return 0.0, 0.0, 0.0, 0.0

    wins = [r for r in settled if r.status == RecommendationStatus.WIN.value]
    hit_rate = (len(wins) / len(settled)) * 100

    staked = STAKE_BASE * len(settled)
    returned = sum(STAKE_BASE * r.odd for r in wins)
    profit_loss = returned - staked
    roi = (profit_loss / staked) * 100 if staked else 0.0

    value_bets_share = (value_bets_total / total_all * 100) if total_all else 0.0
    return hit_rate, roi, profit_loss, value_bets_share


@router.get("/performance", response_model=PerformanceSummary)
async def performance_summary(days: int = Query(30, ge=1, le=365), session: AsyncSession = Depends(get_session)):
    since = datetime.utcnow() - timedelta(days=days)
    previous_since = since - timedelta(days=days)

    current_result = await session.execute(select(Recommendation).where(Recommendation.created_at >= since))
    current_recs = list(current_result.scalars().all())

    previous_result = await session.execute(
        select(Recommendation).where(Recommendation.created_at >= previous_since, Recommendation.created_at < since)
    )
    previous_recs = list(previous_result.scalars().all())

    value_bets_total = sum(1 for r in current_recs if r.is_value_bet)
    hit_rate, roi, profit_loss, value_share = _compute_summary(current_recs, value_bets_total, len(current_recs))

    prev_value_bets_total = sum(1 for r in previous_recs if r.is_value_bet)
    prev_hit_rate, prev_roi, _, _ = _compute_summary(previous_recs, prev_value_bets_total, len(previous_recs))

    return PerformanceSummary(
        period_days=days,
        hit_rate=round(hit_rate, 1),
        hit_rate_delta=round(hit_rate - prev_hit_rate, 1),
        roi=round(roi, 1),
        roi_delta=round(roi - prev_roi, 1),
        profit_loss=round(profit_loss, 2),
        stake_base=STAKE_BASE,
        total_recommendations=len(current_recs),
        value_bets_share=round(value_share, 1),
    )


@router.post("/collect-now")
async def collect_now(session: AsyncSession = Depends(get_session)):
    """Dispara manualmente um ciclo completo (scan + coleta + recomendacao
    + conferencia de resultados) sem esperar o agendador - util para
    testar/demonstrar o sistema na hora."""
    tracked = await scan_live_fixtures(session)
    created = await collect_snapshots(session)
    recommended = await generate_recommendations_for_all_live(session)
    settled = await settle_finished_fixtures(session)
    return {
        "live_fixtures_found": len(tracked),
        "snapshots_created": created,
        "recommendations_updated": recommended,
        "fixtures_settled": settled,
    }
