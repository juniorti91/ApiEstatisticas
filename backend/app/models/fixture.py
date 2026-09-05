from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Fixture(Base):
    """Uma partida (ao vivo, agendada ou finalizada)."""

    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_fixture_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)

    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"))
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))

    round: Mapped[str] = mapped_column(String(80), default="")
    kickoff_at: Mapped[datetime] = mapped_column(DateTime)

    # Status conforme API-Football: NS (nao iniciada), 1H/2H/HT/ET/LIVE (ao vivo),
    # FT/AET/PEN (finalizada), PST/CANC (adiada/cancelada)
    status: Mapped[str] = mapped_column(String(10), default="NS")
    elapsed_minutes: Mapped[int] = mapped_column(Integer, default=0)

    goals_home: Mapped[int] = mapped_column(Integer, default=0)
    goals_away: Mapped[int] = mapped_column(Integer, default=0)

    # Passa a True quando o coletor comeca a monitorar essa partida de 5 em 5 min
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=False)
    # Passa a True quando o tracker ja avaliou as recomendacoes ao final da partida
    results_settled: Mapped[bool] = mapped_column(Boolean, default=False)

    league = relationship("League")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
