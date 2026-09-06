from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HeadToHeadCache(Base):
    """
    Cache dos ultimos confrontos diretos (H2H) entre um PAR de times -
    usado pelo card "H2H pre-jogo". Uma linha por par de times, guardada
    de forma canonica (team_a_id sempre o menor id interno dos dois) pra
    nao duplicar cache quando o mesmo par se enfrenta de novo com
    casa/fora trocados (ver _pair_key em app/services/h2h_service.py).

    Cacheado com validade de horas porque o historico entre dois times so
    muda quando eles jogam de novo um contra o outro - o que normalmente
    leva semanas/meses, bem diferente dos snapshots ao vivo.
    """

    __tablename__ = "head_to_head_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_a_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    team_b_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Cada item: {fixture_api_id, date (ISO, naive UTC), league_name,
    # home_name, away_name, home_goals, away_goals} - mais recente primeiro.
    matches: Mapped[list] = mapped_column(JSON, default=list)

    __table_args__ = (UniqueConstraint("team_a_id", "team_b_id", name="uq_h2h_pair"),)
