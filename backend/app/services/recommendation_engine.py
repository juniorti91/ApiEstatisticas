"""
Motor de recomendacao in-live.

Para cada partida monitorada, compara o ritmo ao vivo (ultimo snapshot)
com a media das ultimas 3-5 partidas de cada time (TeamForm) e projeta o
total esperado ao fim do jogo para alguns mercados. A partir da
probabilidade projetada e da odd (real, quando disponivel na API, ou uma
odd justa sintetica) calcula valor esperado (EV), probabilidade
implicita e uma nota de confianca - o mesmo raciocinio usado no dashboard
de referencia (campo "Justificativa" incluido).

Roda a cada ciclo de coleta (5 min) e faz UPSERT por (fixture, mercado):
enquanto a recomendacao estiver pendente, ela e recalculada com os dados
mais recentes; uma vez que a partida termina, o results_tracker assume e
o motor para de tocar naquela linha.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.stats_math import (
    blended_projection,
    confidence_stars,
    expected_value_pct,
    implied_probability,
    poisson_prob_over,
    project_to_full_match,
)
from app.models.fixture import Fixture
from app.models.odds_history import OddsHistoryPoint
from app.models.recommendation import Recommendation, RecommendationStatus
from app.models.snapshot import MatchSnapshot
from app.models.team import Team
from app.models.team_form import TeamForm
from app.services.odds_service import fetch_raw_odds, find_odd, synthetic_fair_odd
from app.services.team_form_service import get_or_refresh_team_form

logger = logging.getLogger("betanalyzer.recommendation_engine")

MIN_MINUTE_TO_RECOMMEND = 10  # evita recomendar com amostra ao vivo minuscula
MIN_EDGE_TO_STORE = 0.03  # so guarda recomendacao com alguma vantagem estimada sobre odd REAL
MIN_PROBABILITY_WITHOUT_ODD = 0.55  # sem odd real, exige probabilidade estimada minima para exibir


def _confidence_from_probability(prob: float) -> int:
    """Nota de confianca quando nao ha odd real de mercado para comparar -
    baseada diretamente em quao alta e a probabilidade estimada."""
    if prob >= 0.75:
        return 5
    if prob >= 0.65:
        return 4
    if prob >= 0.55:
        return 3
    if prob >= 0.50:
        return 2
    return 1


async def _latest_snapshot(session: AsyncSession, fixture_id: int) -> MatchSnapshot | None:
    result = await session.execute(
        select(MatchSnapshot)
        .where(MatchSnapshot.fixture_id == fixture_id)
        .order_by(MatchSnapshot.minute.desc())
        .limit(1)
    )
    return result.scalars().first()


def _nearest_half_line(projected: float, floor_min: float = 0.5) -> float:
    """Converte uma projecao (ex: 6.8) na linha de aposta mais proxima
    terminada em .5 (ex: 6.5), respeitando um piso minimo."""
    line = round(projected - 0.5) + 0.5
    return max(floor_min, line)


async def _upsert_recommendation(
    session: AsyncSession,
    fixture: Fixture,
    market: str,
    selection: str,
    team_focus: str,
    line: float,
    estimated_probability: float,
    odd: float,
    odd_is_real: bool,
    justification: str,
    minute: int,
) -> Recommendation | None:
    implied = implied_probability(odd)
    edge = estimated_probability - implied

    if odd_is_real:
        # So vale a pena mostrar quando ha vantagem real sobre a odd do mercado.
        if edge < MIN_EDGE_TO_STORE:
            return None
        stars = confidence_stars(estimated_probability, implied)
        value_bet = edge >= 0.03
    else:
        # Sem cotacao real, a "odd justa" foi derivada da propria probabilidade
        # estimada (com margem de casa) - comparar edge contra ela seria
        # circular. Aqui o criterio passa a ser a propria probabilidade
        # estimada ser alta o suficiente para valer a pena exibir, e nunca
        # marcamos como value bet sem uma odd real para comparar.
        if estimated_probability < MIN_PROBABILITY_WITHOUT_ODD:
            return None
        stars = _confidence_from_probability(estimated_probability)
        value_bet = False

    ev = expected_value_pct(estimated_probability, odd)

    result = await session.execute(
        select(Recommendation).where(
            Recommendation.fixture_id == fixture.id,
            Recommendation.market == market,
            Recommendation.status == RecommendationStatus.PENDING.value,
        )
    )
    rec = result.scalars().first()

    odd_note = "odd ao vivo" if odd_is_real else "odd estimada (sem cotacao ao vivo disponivel)"
    full_justification = f"{justification} ({odd_note})."

    if rec is None:
        rec = Recommendation(
            fixture_id=fixture.id,
            market=market,
            selection=selection,
            team_focus=team_focus,
            line=line,
            minute_recommended=minute,
        )
        session.add(rec)

    rec.odd = odd
    rec.estimated_probability = round(estimated_probability, 4)
    rec.implied_probability = round(implied, 4)
    rec.expected_value = round(ev, 2)
    rec.confidence_stars = stars
    rec.is_value_bet = value_bet
    rec.justification = full_justification
    rec.selection = selection
    rec.line = line

    await session.flush()  # garante rec.id para o ponto de historico abaixo
    session.add(
        OddsHistoryPoint(
            recommendation_id=rec.id,
            minute=minute,
            odd=odd,
            estimated_probability=rec.estimated_probability,
        )
    )

    return rec


async def _corner_market(
    session: AsyncSession, fixture: Fixture, snapshot: MatchSnapshot,
    home: Team, away: Team, home_form: TeamForm, away_form: TeamForm, raw_odds: list[dict],
) -> Recommendation | None:
    minute = max(snapshot.minute, 1)

    home_live_proj = project_to_full_match(snapshot.corners_home, minute)
    away_live_proj = project_to_full_match(snapshot.corners_away, minute)
    home_proj = blended_projection(home_live_proj, home_form.avg_corners, minute)
    away_proj = blended_projection(away_live_proj, away_form.avg_corners, minute)

    # Foca no time com ritmo de escanteios mais forte, como no exemplo de referencia
    if home_proj >= away_proj:
        team, team_form, live_count, proj = home, home_form, snapshot.corners_home, home_proj
        team_side = "home"
    else:
        team, team_form, live_count, proj = away, away_form, snapshot.corners_away, away_proj
        team_side = "away"

    line = _nearest_half_line(proj * 0.85)  # linha um pouco abaixo da projecao central
    lam = max(proj, 0.1)
    prob = poisson_prob_over(line, lam)

    raw_odd = find_odd(raw_odds, ["corner"], [f"over {line}", f"+{line}", "over"])
    odd = raw_odd if raw_odd else synthetic_fair_odd(prob)

    opponent_form = away_form if team_side == "home" else home_form
    justification = (
        f"{team.name} tem media de {team_form.avg_corners:.1f} escanteios por jogo nas ultimas "
        f"{team_form.sample_size} partidas. Ja possui {live_count} escanteio(s) aos {minute} minutos "
        f"(projecao de {proj:.1f} ao final). Adversario ({('Fora' if team_side=='home' else 'Casa')}) "
        f"tem media de {opponent_form.avg_corners:.1f} escanteios sofridos/feitos no mesmo recorte"
    )

    return await _upsert_recommendation(
        session, fixture, "corners_over", f"Mais de {line} Escanteios", team.name,
        line, prob, odd, raw_odd is not None, justification, minute,
    )


async def _total_goals_market(
    session: AsyncSession, fixture: Fixture, snapshot: MatchSnapshot,
    home_form: TeamForm, away_form: TeamForm, raw_odds: list[dict],
) -> Recommendation | None:
    minute = max(snapshot.minute, 1)
    current_goals = snapshot.goals_home + snapshot.goals_away

    hist_expected = (home_form.avg_goals_scored + home_form.avg_goals_conceded) / 2 + (
        away_form.avg_goals_scored + away_form.avg_goals_conceded
    ) / 2
    live_proj = project_to_full_match(current_goals, minute)
    proj_total = blended_projection(live_proj, hist_expected, minute)
    remaining_lambda = max(proj_total - current_goals, 0.05)

    line = 1.5 if current_goals <= 1 else current_goals + 0.5
    prob = poisson_prob_over(max(line - current_goals, 0.1), remaining_lambda) if line > current_goals else 0.95

    raw_odd = find_odd(raw_odds, ["goals over/under", "over/under", "total"], [f"over {line}"])
    odd = raw_odd if raw_odd else synthetic_fair_odd(prob)

    justification = (
        f"Media combinada dos dois times projeta {hist_expected:.1f} gols por jogo; no ritmo atual "
        f"({current_goals} gol(s) aos {minute} min) a projecao para os 90 minutos e de {proj_total:.1f} gols"
    )

    return await _upsert_recommendation(
        session, fixture, "total_goals_over", f"Mais de {line} Gols", "",
        line, prob, odd, raw_odd is not None, justification, minute,
    )


async def _btts_market(
    session: AsyncSession, fixture: Fixture, snapshot: MatchSnapshot,
    home_form: TeamForm, away_form: TeamForm, raw_odds: list[dict],
) -> Recommendation | None:
    minute = max(snapshot.minute, 1)
    already_scored_both = snapshot.goals_home > 0 and snapshot.goals_away > 0
    if already_scored_both:
        return None  # mercado ja resolvido, nao faz sentido recomendar

    avg_btts = (home_form.btts_rate + away_form.btts_rate) / 2
    # Quanto mais tempo passa sem os dois marcarem, menor a chance de "sim"
    time_decay = max(0.15, 1 - (minute / 90))
    prob_no = 1 - ((avg_btts / 100) * time_decay)
    prob_no = max(0.05, min(0.95, prob_no))

    raw_odd = find_odd(raw_odds, ["both teams score", "btts"], ["no"])
    odd = raw_odd if raw_odd else synthetic_fair_odd(prob_no)

    justification = (
        f"Media das ultimas partidas mostra ambos marcam em {avg_btts:.0f}% dos jogos dos dois times; "
        f"aos {minute} minutos o placar ainda nao teve gols dos dois lados, reduzindo essa chance"
    )

    return await _upsert_recommendation(
        session, fixture, "btts_no", "Ambos Marcam - Nao", "",
        0, prob_no, odd, raw_odd is not None, justification, minute,
    )


async def generate_recommendations_for_fixture(session: AsyncSession, fixture: Fixture) -> list[Recommendation]:
    snapshot = await _latest_snapshot(session, fixture.id)
    if snapshot is None or snapshot.minute < MIN_MINUTE_TO_RECOMMEND:
        return []

    home = await session.get(Team, fixture.home_team_id)
    away = await session.get(Team, fixture.away_team_id)
    home_form = await get_or_refresh_team_form(session, home)
    away_form = await get_or_refresh_team_form(session, away)
    raw_odds = await fetch_raw_odds(fixture.api_fixture_id)

    candidates = [
        await _corner_market(session, fixture, snapshot, home, away, home_form, away_form, raw_odds),
        await _total_goals_market(session, fixture, snapshot, home_form, away_form, raw_odds),
        await _btts_market(session, fixture, snapshot, home_form, away_form, raw_odds),
    ]
    recs = [r for r in candidates if r is not None]

    # Marca a de maior EV como recomendacao principal do jogo
    for r in recs:
        r.is_primary = False
    if recs:
        best = max(recs, key=lambda r: r.expected_value)
        best.is_primary = True

    await session.commit()
    logger.info("Fixture %s: %d recomendacao(oes) atualizada(s).", fixture.api_fixture_id, len(recs))
    return recs


async def generate_recommendations_for_all_live(session: AsyncSession) -> int:
    result = await session.execute(
        select(Fixture).where(Fixture.is_monitored.is_(True), Fixture.status.in_(
            ["1H", "2H", "HT", "ET", "BT", "P", "LIVE"]
        ))
    )
    fixtures = list(result.scalars().all())
    total = 0
    for fixture in fixtures:
        recs = await generate_recommendations_for_fixture(session, fixture)
        total += len(recs)
    return total
