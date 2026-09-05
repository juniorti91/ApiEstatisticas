from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MatchSnapshot(Base):
    """
    Uma 'fotografia' do estado da partida, capturada a cada N minutos
    (padrao 5) enquanto ela esta ao vivo. E a base para os graficos de
    evolucao e para o motor de recomendacao.
    """

    __tablename__ = "match_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)

    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    minute: Mapped[int] = mapped_column(Integer)

    goals_home: Mapped[int] = mapped_column(Integer, default=0)
    goals_away: Mapped[int] = mapped_column(Integer, default=0)

    possession_home: Mapped[float] = mapped_column(Float, default=0)
    possession_away: Mapped[float] = mapped_column(Float, default=0)

    shots_on_target_home: Mapped[int] = mapped_column(Integer, default=0)
    shots_on_target_away: Mapped[int] = mapped_column(Integer, default=0)
    shots_off_target_home: Mapped[int] = mapped_column(Integer, default=0)
    shots_off_target_away: Mapped[int] = mapped_column(Integer, default=0)
    total_shots_home: Mapped[int] = mapped_column(Integer, default=0)
    total_shots_away: Mapped[int] = mapped_column(Integer, default=0)

    corners_home: Mapped[int] = mapped_column(Integer, default=0)
    corners_away: Mapped[int] = mapped_column(Integer, default=0)

    yellow_cards_home: Mapped[int] = mapped_column(Integer, default=0)
    yellow_cards_away: Mapped[int] = mapped_column(Integer, default=0)
    red_cards_home: Mapped[int] = mapped_column(Integer, default=0)
    red_cards_away: Mapped[int] = mapped_column(Integer, default=0)

    fouls_home: Mapped[int] = mapped_column(Integer, default=0)
    fouls_away: Mapped[int] = mapped_column(Integer, default=0)
    offsides_home: Mapped[int] = mapped_column(Integer, default=0)
    offsides_away: Mapped[int] = mapped_column(Integer, default=0)

    dangerous_attacks_home: Mapped[int] = mapped_column(Integer, default=0)
    dangerous_attacks_away: Mapped[int] = mapped_column(Integer, default=0)

    # Campos adicionados para a tela detalhada de "Partidas Ao Vivo" (ver
    # app/services/stats_mapper.py). Colunas novas numa tabela ja existente
    # nao sao criadas pelo create_all do SQLAlchemy - a migracao leve que
    # adiciona essas colunas ao banco ja existente fica em app/database.py
    # (_ensure_snapshot_columns).
    shots_blocked_home: Mapped[int] = mapped_column(Integer, default=0)
    shots_blocked_away: Mapped[int] = mapped_column(Integer, default=0)
    shots_inside_box_home: Mapped[int] = mapped_column(Integer, default=0)
    shots_inside_box_away: Mapped[int] = mapped_column(Integer, default=0)
    shots_outside_box_home: Mapped[int] = mapped_column(Integer, default=0)
    shots_outside_box_away: Mapped[int] = mapped_column(Integer, default=0)

    passes_total_home: Mapped[int] = mapped_column(Integer, default=0)
    passes_total_away: Mapped[int] = mapped_column(Integer, default=0)
    passes_accurate_home: Mapped[int] = mapped_column(Integer, default=0)
    passes_accurate_away: Mapped[int] = mapped_column(Integer, default=0)
    passes_pct_home: Mapped[float] = mapped_column(Float, default=0)
    passes_pct_away: Mapped[float] = mapped_column(Float, default=0)

    goalkeeper_saves_home: Mapped[int] = mapped_column(Integer, default=0)
    goalkeeper_saves_away: Mapped[int] = mapped_column(Integer, default=0)

    xg_home: Mapped[float] = mapped_column(Float, default=0)
    xg_away: Mapped[float] = mapped_column(Float, default=0)
