from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.fixture import Fixture
from app.models.snapshot import MatchSnapshot
from app.models.team import Team
from app.schemas.comparison import ComparisonMetric, MatchComparison
from app.schemas.detailed_stats import DetailedMatchStats, PlayerRatingOut, TeamDetailedStats
from app.schemas.fixture import FixtureOut
from app.schemas.h2h import H2HMatchOut, H2HOut
from app.schemas.lineup import MatchLineupOut
from app.schemas.match_events import MatchEventOut, MatchEventsOut
from app.schemas.prognostics import (
    AnomalyRowOut,
    GoalWindowOut,
    MomentumOut,
    NextGoalOut,
    PrognosticsOut,
    WinProbabilityOut,
)
from app.schemas.snapshot import ManualSnapshotIn, MatchSnapshotOut
from app.schemas.stat_comparison import StatComparisonOut, StatComparisonRow
from app.services.collector import track_fixture_by_id
from app.services.events_service import get_or_refresh_events
from app.services.h2h_service import get_or_refresh_h2h
from app.services.lineup_service import get_or_refresh_lineup
from app.services.prognostics_service import (
    compute_anomaly_summary,
    compute_goal_window_probability,
    compute_momentum,
    compute_next_goal_probability,
    compute_remaining_goal_expectation,
    compute_win_probability,
)
from app.services.stat_window_service import build_stat_rows
from app.services.team_form_service import get_or_refresh_team_form

logger = logging.getLogger("betanalyzer.matches")

router = APIRouter(prefix="/api/matches", tags=["matches"])

LIVE_STATUSES = ["1H", "2H", "HT", "ET", "BT", "P", "LIVE"]
# Minuto minimo pra confiar nos modelos de prognostico (probabilidade de
# vitoria/gol, momentum) - antes disso ha snapshot(s) de menos pra dizer
# qualquer coisa util, mesmo com a media historica ajudando a suavizar
# (ver blended_projection em prognostics_service.py).
MIN_MINUTE_FOR_PROGNOSTICS = 5


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


@router.get("/{fixture_id}/stat-comparison", response_model=StatComparisonOut)
async def get_stat_comparison(
    fixture_id: int, window: int | None = None, session: AsyncSession = Depends(get_session)
):
    """Comparativo casa x fora com varias metricas, usado na tela
    "Comparativo Detalhado" - so leitura dos snapshots ja salvos (sem
    chamada nova a API-Football, igual detailed-stats acima). `window` em
    minutos (5/10/15) recalcula so pra essa janela recente em vez do
    acumulado do jogo todo - ver app/services/stat_window_service.py para
    o raciocinio de como cada metrica e recalculada numa janela."""
    fixture = await session.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    result = await session.execute(
        select(MatchSnapshot).where(MatchSnapshot.fixture_id == fixture_id).order_by(MatchSnapshot.minute)
    )
    snapshots = list(result.scalars().all())

    rows, from_minute, to_minute = build_stat_rows(snapshots, window)
    return StatComparisonOut(
        window_minutes=window,
        from_minute=from_minute,
        to_minute=to_minute,
        rows=[StatComparisonRow(key=r.key, label=r.label, home=r.home, away=r.away) for r in rows],
    )


@router.get("/{fixture_id}/lineups", response_model=MatchLineupOut)
async def get_lineups(fixture_id: int, session: AsyncSession = Depends(get_session)):
    """Escalação provável/titular, técnicos, árbitro e lesões/suspensões
    da partida, para a tela "Escalações" - cacheado por horas (ver
    app/services/lineup_service.py), já que essa informação não muda
    durante o jogo."""
    fixture = await session.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    cache = await get_or_refresh_lineup(session, fixture)
    if cache is None:
        return MatchLineupOut(lineup_available=False)

    return MatchLineupOut(
        referee=cache.referee,
        formation_home=cache.formation_home,
        formation_away=cache.formation_away,
        coach_home=cache.coach_home,
        coach_away=cache.coach_away,
        lineup_home=cache.lineup_home or [],
        lineup_away=cache.lineup_away or [],
        substitutes_home=cache.substitutes_home or [],
        substitutes_away=cache.substitutes_away or [],
        injuries_home=cache.injuries_home or [],
        injuries_away=cache.injuries_away or [],
        lineup_available=bool(cache.lineup_home or cache.lineup_away),
    )


@router.get("/{fixture_id}/h2h", response_model=H2HOut)
async def get_h2h(fixture_id: int, session: AsyncSession = Depends(get_session)):
    """Ultimos confrontos diretos entre os dois times da partida, para o
    card "H2H pre-jogo" - cacheado por par de times (ver
    app/services/h2h_service.py), ja que o historico entre dois times so
    muda quando eles jogam de novo um contra o outro."""
    fixture = await session.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    home_team = await session.get(Team, fixture.home_team_id)
    away_team = await session.get(Team, fixture.away_team_id)
    cache = await get_or_refresh_h2h(session, home_team, away_team)
    if cache is None:
        return H2HOut(matches=[])

    # A tela mostra so os confrontos mais recentes (ver referencia: 3-5
    # jogos) - o cache guarda mais (FETCH_LAST) so pra nao precisar
    # rebuscar na API se um dia quisermos mostrar mais no frontend.
    matches = (cache.matches or [])[:5]
    return H2HOut(matches=[H2HMatchOut(**m) for m in matches])


@router.get("/{fixture_id}/events", response_model=MatchEventsOut)
async def get_events(fixture_id: int, session: AsyncSession = Depends(get_session)):
    """Eventos (gols, cartoes, substituicoes, VAR) da partida, para a
    linha do tempo de eventos na aba Eventos - cacheado com validade curta
    enquanto o jogo esta ao vivo (ver app/services/events_service.py)."""
    fixture = await session.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    cache = await get_or_refresh_events(session, fixture)
    if cache is None:
        return MatchEventsOut(events=[])

    return MatchEventsOut(events=[MatchEventOut(**e) for e in (cache.events or [])])


@router.get("/{fixture_id}/prognostics", response_model=PrognosticsOut)
async def get_prognostics(fixture_id: int, session: AsyncSession = Depends(get_session)):
    """Probabilidade de vitoria (1X2), probabilidade de proximo gol,
    probabilidade de gol nos proximos 5/10min, indice de Momentum e um
    resumo do indice de anomalia - tudo calculado em cima dos snapshots e
    do TeamForm que ja existem (nenhuma chamada nova a API-Football, ver
    app/services/prognostics_service.py para o raciocinio de cada
    modelo)."""
    fixture = await session.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    result = await session.execute(
        select(MatchSnapshot).where(MatchSnapshot.fixture_id == fixture_id).order_by(MatchSnapshot.minute)
    )
    snapshots = list(result.scalars().all())

    if not snapshots or snapshots[-1].minute < MIN_MINUTE_FOR_PROGNOSTICS:
        return PrognosticsOut(
            minute=snapshots[-1].minute if snapshots else 0,
            insufficient_data=True,
            win_probability=WinProbabilityOut(home=1 / 3, draw=1 / 3, away=1 / 3),
            next_goal=NextGoalOut(home=0.5, away=0.5),
            goal_windows=GoalWindowOut(home_5min=0, away_5min=0, home_10min=0, away_10min=0),
            momentum=MomentumOut(),
            anomalies=[],
        )

    latest = snapshots[-1]
    minute = latest.minute

    home = await session.get(Team, fixture.home_team_id)
    away = await session.get(Team, fixture.away_team_id)
    home_form = await get_or_refresh_team_form(session, home)
    away_form = await get_or_refresh_team_form(session, away)

    remaining_home, remaining_away = compute_remaining_goal_expectation(
        latest.goals_home, latest.goals_away, minute, home_form, away_form
    )
    win_prob = compute_win_probability(latest.goals_home, latest.goals_away, remaining_home, remaining_away)
    next_goal = compute_next_goal_probability(remaining_home, remaining_away)
    goal_windows = compute_goal_window_probability(remaining_home, remaining_away, minute)
    momentum = compute_momentum(snapshots)
    anomalies = compute_anomaly_summary(latest, minute, home_form, away_form)

    return PrognosticsOut(
        minute=minute,
        insufficient_data=False,
        win_probability=WinProbabilityOut(home=win_prob.home, draw=win_prob.draw, away=win_prob.away),
        next_goal=NextGoalOut(home=next_goal.home, away=next_goal.away),
        goal_windows=GoalWindowOut(
            home_5min=goal_windows.home_5min,
            away_5min=goal_windows.away_5min,
            home_10min=goal_windows.home_10min,
            away_10min=goal_windows.away_10min,
        ),
        momentum=MomentumOut(
            home=momentum.home,
            away=momentum.away,
            home_delta=momentum.home_delta,
            away_delta=momentum.away_delta,
            home_trend=momentum.home_trend,
            away_trend=momentum.away_trend,
        ),
        anomalies=[AnomalyRowOut(label=a.label, home_pct=a.home_pct, away_pct=a.away_pct) for a in anomalies],
    )


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


@router.get("/{fixture_id}/detailed-stats", response_model=DetailedMatchStats)
async def get_detailed_stats(fixture_id: int, session: AsyncSession = Depends(get_session)):
    """
    Estatisticas detalhadas para a tela "Partidas Ao Vivo". Desde que
    `collect_snapshots` (ver services/collector.py) passou a buscar
    TAMBEM /fixtures/players a cada ciclo de coleta, tudo aqui - inclusive
    duelos, dribles, desarmes e as notas dos jogadores - ja vem pronto do
    ultimo snapshot salvo. Este endpoint nao faz mais nenhuma chamada a
    API-Football: e so leitura do banco, entao pode ser chamado a vontade
    (inclusive no polling normal da tela) sem custo extra de cota.
    """
    fixture = await session.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    snap_result = await session.execute(
        select(MatchSnapshot).where(MatchSnapshot.fixture_id == fixture_id).order_by(MatchSnapshot.minute.desc()).limit(1)
    )
    snapshot = snap_result.scalars().first()

    def base_team_stats(prefix: str) -> TeamDetailedStats:
        if snapshot is None:
            return TeamDetailedStats()
        return TeamDetailedStats(
            shots_blocked=getattr(snapshot, f"shots_blocked_{prefix}", 0) or 0,
            shots_inside_box=getattr(snapshot, f"shots_inside_box_{prefix}", 0) or 0,
            shots_outside_box=getattr(snapshot, f"shots_outside_box_{prefix}", 0) or 0,
            passes_total=getattr(snapshot, f"passes_total_{prefix}", 0) or 0,
            passes_accurate=getattr(snapshot, f"passes_accurate_{prefix}", 0) or 0,
            passes_pct=getattr(snapshot, f"passes_pct_{prefix}", 0) or 0,
            goalkeeper_saves=getattr(snapshot, f"goalkeeper_saves_{prefix}", 0) or 0,
            xg=getattr(snapshot, f"xg_{prefix}", 0) or 0,
            duels_total=getattr(snapshot, f"duels_total_{prefix}", 0) or 0,
            duels_won=getattr(snapshot, f"duels_won_{prefix}", 0) or 0,
            dribbles_attempts=getattr(snapshot, f"dribbles_attempts_{prefix}", 0) or 0,
            dribbles_success=getattr(snapshot, f"dribbles_success_{prefix}", 0) or 0,
            tackles_total=getattr(snapshot, f"tackles_total_{prefix}", 0) or 0,
            interceptions=getattr(snapshot, f"interceptions_{prefix}", 0) or 0,
            passes_key=getattr(snapshot, f"passes_key_{prefix}", 0) or 0,
            fouls_committed=getattr(snapshot, f"fouls_committed_{prefix}", 0) or 0,
            fouls_drawn=getattr(snapshot, f"fouls_drawn_{prefix}", 0) or 0,
        )

    home_stats = base_team_stats("home")
    away_stats = base_team_stats("away")

    top_players_home = [PlayerRatingOut(**p) for p in (snapshot.top_players_home if snapshot else []) or []]
    top_players_away = [PlayerRatingOut(**p) for p in (snapshot.top_players_away if snapshot else []) or []]
    player_stats_available = bool(snapshot.player_stats_available) if snapshot else True

    return DetailedMatchStats(
        home=home_stats,
        away=away_stats,
        top_players_home=top_players_home,
        top_players_away=top_players_away,
        player_stats_available=player_stats_available,
    )
