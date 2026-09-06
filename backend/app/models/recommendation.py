from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecommendationStatus(str, Enum):
    PENDING = "pending"
    WIN = "win"
    LOSS = "loss"
    VOID = "void"


class Recommendation(Base):
    """
    Uma entrada sugerida pelo motor de recomendacao para uma partida ao
    vivo (ex: "Manchester City - Mais de 5.5 Escanteios"), junto com a
    justificativa estatistica e, ao final da partida, o resultado.
    """

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)

    market: Mapped[str] = mapped_column(String(60))  # ex: "corners_over"
    selection: Mapped[str] = mapped_column(String(160))  # texto exibido, ex: "Mais de 5.5 Escanteios"
    team_focus: Mapped[str] = mapped_column(String(120), default="")  # time referenciado, se houver
    line: Mapped[float] = mapped_column(Float, default=0)

    odd: Mapped[float] = mapped_column(Float, default=0)
    # True = odd real veio do /odds/live (mercado ao vivo de verdade);
    # False = nenhum mercado ao vivo foi encontrado pra essa selecao nesse
    # momento e a odd exibida e uma estimativa sintetica derivada da
    # probabilidade calculada (ver odds_service.synthetic_fair_odd); None
    # = registro criado antes dessa coluna existir, estado desconhecido.
    # Existe pra o front poder avisar claramente "AO VIVO" vs "ESTIMADA"
    # ao lado da odd, em vez de essa info ficar escondida so no texto da
    # justificativa.
    odd_is_live: Mapped[bool | None] = mapped_column(Integer, nullable=True, default=None)
    estimated_probability: Mapped[float] = mapped_column(Float)  # 0-1
    implied_probability: Mapped[float] = mapped_column(Float)  # 0-1
    expected_value: Mapped[float] = mapped_column(Float)  # em % (EV)
    confidence_stars: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    is_value_bet: Mapped[bool] = mapped_column(Integer, default=0)  # 0/1 (bool)

    justification: Mapped[str] = mapped_column(String(1000), default="")

    minute_recommended: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # Diferente de created_at (so marca quando a linha nasceu e nunca muda
    # depois): atualizada TODA VEZ que o motor de recomendacao roda pra
    # essa partida/mercado (a cada ciclo de odds, ~60s), mesmo quando o
    # valor final da odd/probabilidade acaba saindo identico ao anterior.
    # Existe pra o usuario conseguir ver na tela se uma recomendacao
    # realmente esta sendo recalculada ("atualizado as HH:MM:SS" andando
    # pra frente a cada minuto) ou se ficou travada com dado velho - sem
    # isso nao tinha como distinguir "recalculou e deu o mesmo valor" de
    # "parou de recalcular". None = registro criado antes dessa coluna
    # existir.
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    status: Mapped[str] = mapped_column(String(10), default=RecommendationStatus.PENDING.value)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    final_stat_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_primary: Mapped[bool] = mapped_column(Integer, default=0)  # destaque como "Recomendacao Principal"
