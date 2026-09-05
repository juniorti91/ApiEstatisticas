from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OddsHistoryPoint(Base):
    """
    Um ponto no tempo da evolucao de uma recomendacao: odd e probabilidade
    estimada no momento em que o motor recalculou aquele mercado (a cada
    ciclo de coleta). Alimenta o grafico de "Movimentacao das Odds" e
    tambem serve de trilha de auditoria de como a recomendacao mudou ao
    longo da partida.
    """

    __tablename__ = "odds_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    minute: Mapped[int] = mapped_column(Integer, default=0)
    odd: Mapped[float] = mapped_column(Float)
    estimated_probability: Mapped[float] = mapped_column(Float)
