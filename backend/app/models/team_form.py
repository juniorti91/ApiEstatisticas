from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TeamForm(Base):
    """
    Medias de desempenho de um time nas suas ultimas N partidas (3 ou 5),
    recalculadas periodicamente a partir do historico da API-Football e
    usadas pelo motor de recomendacao como linha de base ("Media dos
    ultimos 5 jogos" no dashboard).

    UMA linha por time (ver UniqueConstraint abaixo) - corrigido apos um
    bug real em producao (MultipleResultsFound derrubando /prognostics):
    sem essa restricao, duas requisicoes concorrentes pro mesmo time
    conseguiam cada uma inserir sua propria linha (ver o "await" no meio
    do calculo em app/services/team_form_service.py, que cede o event
    loop e abre a janela de corrida). Bancos SQLite ja existentes recebem
    esse indice via migracao leve em app/database.py (que tambem remove
    duplicatas ja gravadas antes da correcao).
    """

    __tablename__ = "team_form"
    __table_args__ = (UniqueConstraint("team_id", name="uq_team_form_team_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=5)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    avg_shots: Mapped[float] = mapped_column(Float, default=0)
    avg_shots_on_target: Mapped[float] = mapped_column(Float, default=0)
    avg_corners: Mapped[float] = mapped_column(Float, default=0)
    avg_goals_scored: Mapped[float] = mapped_column(Float, default=0)
    avg_goals_conceded: Mapped[float] = mapped_column(Float, default=0)
    avg_possession: Mapped[float] = mapped_column(Float, default=0)
    avg_yellow_cards: Mapped[float] = mapped_column(Float, default=0)
    avg_fouls: Mapped[float] = mapped_column(Float, default=0)
    btts_rate: Mapped[float] = mapped_column(Float, default=0)  # % jogos com ambos marcam
    over_2_5_rate: Mapped[float] = mapped_column(Float, default=0)
