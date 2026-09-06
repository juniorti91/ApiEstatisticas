from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FixtureEventsCache(Base):
    """
    Cache dos eventos (gols, cartoes, substituicoes, VAR) de uma partida -
    usado pela linha do tempo de eventos ("momentum") na aba Eventos.

    Uma linha por partida (fixture_id e unico), atualizada no lugar. Ao
    contrario da escalacao/arbitro (que nao mudam mais depois de
    publicados), eventos ACONTECEM ao vivo - por isso o cache usa uma
    validade bem curta (segundos, nao horas) enquanto a partida esta em
    andamento, e so vira "estavel" (validade longa) quando o jogo termina
    (ver app/services/events_service.py).
    """

    __tablename__ = "fixture_events_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), unique=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Cada item: {"minute": int, "extra_minute": int|None, "side":
    # "home"/"away", "type": "Goal"/"Card"/"subst"/"Var", "detail": str,
    # "player_name": str|None, "assist_name": str|None}.
    events: Mapped[list] = mapped_column(JSON, default=list)
