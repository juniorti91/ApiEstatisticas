from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.fixture import Fixture
from app.models.snapshot import MatchSnapshot
from app.models.team import Team
from app.schemas.comparison import ComparisonMetric, MatchComparison
from app.schemas.fixture import FixtureOut
from app.schemas.snapshot import ManualSnapshotIn, MatchSnapshotOut
from app.services.collector import track_fixture_by_id
from app.services.team_form_service import get_or_refresh_team_form

router = APIRouter(prefix="/api/matches", tags=["matches"])

LIVE_STATUSES = ["1H", "2H", "HT", "ET", "BT", "P", "LIVE"]


def _fixture_query():
    return select(Fixture).options(
        selectinload(Fixture.league), selectinload(Fixture.home_team), selectinload(Fixture.away_team)
    )


@router.get("/live", response_model=list[FixtureOut])
async def list_live_matches(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        _fixture_query().where(Fixture.is_monitored.is_(True), Fixture.status.in_(LIVE_STATUSES))
    )
    return result.scalars().all()


@router.get("/{fixture_id}", response_model=FixtureOut)
async def get_match(fixture_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(_fixture_query().where(Fixture.id == fixture_id))
    fixture = result.scalars().first()
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")
    return fixture


@router.get("/{fixture_id}/snapshots", response_model=list[MatchSnapshotOut])
async def list_snapshots(fixture_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(MatchSnapshot).where(MatchSnapshot.fixture_id == fixture_id).order_by(MatchSnapshot.minute)
    )
    return result.scalars().all()


@router.post("/{fixture_id}/snapshots/manual", response_model=MatchSnapshotOut)
async def add_manual_snapshot(
    fixture_id: int, payload: ManualSnapshotIn, session: AsyncSession = Depends(get_session)
):
    """Insercao manual de estatisticas - fallback para quando nao ha
    cobertura da API para a partida (conforme pedido: coleta via API OU
    insercao manual)."""
    fixture = await session.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    snapshot = MatchSnapshot(fixture_id=fixture_id, **payload.model_dump())
    session.add(snapshot)

    fixture.elapsed_minutes = payload.minute
    fixture.goals_home = payload.goals_home
    fixture.goals_away = payload.goals_away
    fixture.is_monitored = True

    await session.commit()
    await session.refresh(snapshot)
    return snapshot


@router.post("/track/{api_fixture_id}", response_model=FixtureOut)
async def track_match(api_fixture_id: int, session: AsyncSession = Depends(get_session)):
    """Passa a monitorar manualmente uma partida especifica pelo ID da
    API-Football (util para partidas fora das ligas padrao)."""
    fixture = await track_fixture_by_id(session, api_fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Nao foi possivel localizar essa partida na API-Football")
    result = await session.execute(_fixture_query().where(Fixture.id == fixture.id))
    return result.scalars().first()


@router.get("/{fixture_id}/comparison", response_model=MatchComparison)
async def get_comparison(fixture_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(_fixture_query().where(Fixture.id == fixture_id))
    fixture = result.scalars().first()
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    snap_result = await session.execute(
        select(MatchSnapshot).where(MatchSnapshot.fixture_id == fixture_id).order_by(MatchSnapshot.minute.desc()).limit(1)
    )
    snapshot = snap_result.scalars().first()

    home = await session.get(Team, fixture.home_team_id)
    away = await session.get(Team, fixture.away_team_id)
    home_form = await get_or_refresh_team_form(session, home)
    away_form = await get_or_refresh_team_form(session, away)

    def trend(current: float, avg: float) -> str:
        if current > avg * 1.05:
            return "up"
        if current < avg * 0.95:
            return "down"
        return "flat"

    s = snapshot
    metrics = [
        ComparisonMetric(
            label="Finalizacoes", home_avg_last=home_form.avg_shots, away_avg_last=away_form.avg_shots,
            home_current=s.total_shots_home if s else 0, away_current=s.total_shots_away if s else 0,
            home_trend=trend(s.total_shots_home if s else 0, home_form.avg_shots),
            away_trend=trend(s.total_shots_away if s else 0, away_form.avg_shots),
        ),
        ComparisonMetric(
            label="Finalizacoes no alvo", home_avg_last=home_form.avg_shots_on_target,
            away_avg_last=away_form.avg_shots_on_target,
            home_current=s.shots_on_target_home if s else 0, away_current=s.shots_on_target_away if s else 0,
            home_trend=trend(s.shots_on_target_home if s else 0, home_form.avg_shots_on_target),
            away_trend=trend(s.shots_on_target_away if s else 0, away_form.avg_shots_on_target),
        ),
        ComparisonMetric(
            label="Escanteios", home_avg_last=home_form.avg_corners, away_avg_last=away_form.avg_corners,
            home_current=s.corners_home if s else 0, away_current=s.corners_away if s else 0,
            home_trend=trend(s.corners_home if s else 0, home_form.avg_corners),
            away_trend=trend(s.corners_away if s else 0, away_form.avg_corners),
        ),
        ComparisonMetric(
            label="Gols marcados", home_avg_last=home_form.avg_goals_scored, away_avg_last=away_form.avg_goals_scored,
            home_current=fixture.goals_home, away_current=fixture.goals_away,
            home_trend=trend(fixture.goals_home, home_form.avg_goals_scored),
            away_trend=trend(fixture.goals_away, away_form.avg_goals_scored),
        ),
        ComparisonMetric(
            label="Posse de bola (%)", home_avg_last=home_form.avg_possession, away_avg_last=away_form.avg_possession,
            home_current=s.possession_home if s else 0, away_current=s.possession_away if s else 0,
            home_trend=trend(s.possession_home if s else 0, home_form.avg_possession),
            away_trend=trend(s.possession_away if s else 0, away_form.avg_possession),
        ),
    ]

    return MatchComparison(sample_size=home_form.sample_size or 5, metrics=metrics)
