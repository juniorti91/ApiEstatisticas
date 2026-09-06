from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.team import Team
from app.schemas.team_history import TeamHistoryMatchOut
from app.services.team_history_service import get_or_refresh_team_history

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("/{team_id}/history", response_model=list[TeamHistoryMatchOut])
async def get_team_history(team_id: int, session: AsyncSession = Depends(get_session)):
    """Historico recente do time (gols, mando de campo, competicao, placar
    do intervalo) para a tela "Comparativo Histórico" - os filtros de
    quantidade de jogos/mando/competicao sao aplicados no FRONTEND em cima
    dessa lista (ver docstring de team_history_service.py pro porque)."""
    team = await session.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Time nao encontrado")
    return await get_or_refresh_team_history(session, team)
