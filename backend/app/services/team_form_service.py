"""
Calcula e mantem em cache a "forma" de cada time: medias das ultimas 3-5
partidas, usadas pelo motor de recomendacao como linha de base de
comparacao com o desempenho ao vivo.

E recalculado sob demanda (nao a cada 5 minutos, para nao estourar o
limite de chamadas da API) - so quando o cache esta ausente ou mais velho
que `max_age_hours`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.team import Team
from app.models.team_form import TeamForm
from app.services.api_football_client import ApiFootballError, api_football_client
from app.services.stats_mapper import extract_side

logger = logging.getLogger("betanalyzer.team_form")


async def _latest_form(session: AsyncSession, team_id: int) -> TeamForm | None:
    """Busca o TeamForm mais recente de um time - TOLERANTE a mais de uma
    linha existir pro mesmo team_id (ver comentario grande abaixo sobre a
    corrida que causava isso). Usar scalar_one_or_none() aqui quebrava com
    MultipleResultsFound assim que uma duplicata acontecia, derrubando
    /prognostics e o ciclo de recomendacoes pra aquele time PERMANENTEMENTE
    (toda chamada seguinte batia no mesmo erro) - agora so pega a mais
    atualizada e segue em frente."""
    result = await session.execute(
        select(TeamForm).where(TeamForm.team_id == team_id).order_by(TeamForm.updated_at.desc())
    )
    return result.scalars().first()


async def get_or_refresh_team_form(
    session: AsyncSession,
    team: Team,
    sample_size: int | None = None,
    max_age_hours: int = 12,
) -> TeamForm:
    sample_size = sample_size or settings.team_form_sample_size
    form = await _latest_form(session, team.id)

    is_stale = form is None or (datetime.utcnow() - form.updated_at) > timedelta(hours=max_age_hours)
    if not is_stale:
        return form

    try:
        recent = await api_football_client.team_last_fixtures(team.api_id, last=sample_size)
    except ApiFootballError as exc:
        logger.warning("Falha ao buscar ultimas partidas do time %s: %s", team.name, exc)
        if form is not None:
            return form  # usa cache antigo em vez de falhar
        return await _empty_form(session, team, sample_size)

    if not recent:
        return form if form is not None else await _empty_form(session, team, sample_size)

    shots, shots_on_target, corners, fouls, yellow_cards, possession = [], [], [], [], [], []
    goals_scored, goals_conceded = [], []
    btts_count, over_25_count = 0, 0

    for raw_fixture in recent:
        fixture_id = raw_fixture["fixture"]["id"]
        home = raw_fixture["teams"]["home"]
        away = raw_fixture["teams"]["away"]
        goals = raw_fixture.get("goals", {})
        is_home = home["id"] == team.api_id

        scored = (goals.get("home") if is_home else goals.get("away")) or 0
        conceded = (goals.get("away") if is_home else goals.get("home")) or 0
        goals_scored.append(scored)
        goals_conceded.append(conceded)
        if (goals.get("home") or 0) > 0 and (goals.get("away") or 0) > 0:
            btts_count += 1
        if ((goals.get("home") or 0) + (goals.get("away") or 0)) > 2.5:
            over_25_count += 1

        try:
            raw_stats = await api_football_client.fixture_statistics(fixture_id)
        except ApiFootballError:
            continue

        for entry in raw_stats:
            if entry.get("team", {}).get("id") != team.api_id:
                continue
            parsed = extract_side(entry.get("statistics", []))
            shots.append(parsed["total_shots"])
            shots_on_target.append(parsed["shots_on_target"])
            corners.append(parsed["corners"])
            fouls.append(parsed["fouls"])
            yellow_cards.append(parsed["yellow_cards"])
            possession.append(parsed["possession"])

    def avg(values: list[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    n = len(recent)
    is_new = form is None
    if is_new:
        form = TeamForm(team_id=team.id, sample_size=sample_size)
        session.add(form)

    form.sample_size = sample_size
    form.updated_at = datetime.utcnow()
    form.avg_shots = avg(shots)
    form.avg_shots_on_target = avg(shots_on_target)
    form.avg_corners = avg(corners)
    form.avg_goals_scored = avg(goals_scored)
    form.avg_goals_conceded = avg(goals_conceded)
    form.avg_yellow_cards = avg(yellow_cards)
    form.avg_fouls = avg(fouls)
    form.avg_possession = avg(possession)
    form.btts_rate = round((btts_count / n) * 100, 1) if n else 0.0
    form.over_2_5_rate = round((over_25_count / n) * 100, 1) if n else 0.0

    if is_new:
        # CORRIGIDO - causa raiz do MultipleResultsFound: como o intervalo
        # entre o SELECT la em cima e este COMMIT inclui varias chamadas
        # `await` a API-Football (que cedem o controle pro event loop),
        # duas requisicoes concorrentes pro MESMO time (ex: ele aparece
        # como mandante numa partida e visitante em outra, ambas sendo
        # exibidas ao mesmo tempo no dashboard) podiam ver "nenhum form
        # ainda" ao mesmo tempo e cada uma inserir sua propria linha - a
        # tabela nao tinha nenhuma restricao de unicidade em team_id pra
        # impedir isso (ver migracao em app/database.py, que agora cria um
        # indice UNIQUE). Com o indice, a segunda tentativa cai aqui: em
        # vez de derrubar a requisicao, descarta a insercao e usa a linha
        # que a outra requisicao concorrente ja gravou.
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            winner = await _latest_form(session, team.id)
            if winner is not None:
                return winner
            raise  # nao deveria acontecer (colisao mas sem linha nenhuma la) - deixa estourar
    else:
        await session.commit()

    await session.refresh(form)
    return form


async def _empty_form(session: AsyncSession, team: Team, sample_size: int) -> TeamForm:
    form = TeamForm(team_id=team.id, sample_size=sample_size, updated_at=datetime.utcnow())
    session.add(form)
    try:
        await session.commit()
    except IntegrityError:
        # Mesma corrida documentada acima, so que no caminho de "form
        # vazio" (times sem partidas anteriores na API ainda).
        await session.rollback()
        winner = await _latest_form(session, team.id)
        if winner is not None:
            return winner
        raise
    await session.refresh(form)
    return form
