from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Float
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

    # Agregados de /fixtures/players (duelos, dribles, desarmes,
    # interceptacoes, passes-chave, faltas) - ate aqui so eram buscados
    # sob demanda quando o usuario abria a tela de detalhes. Agora o
    # proprio collect_snapshots busca isso a cada ciclo (ver collector.py),
    # entao esses campos passam a ter um HISTORICO no tempo, igual o resto
    # do snapshot - custam 1 requisicao de API a mais por partida
    # monitorada a cada ciclo de coleta.
    duels_total_home: Mapped[int] = mapped_column(Integer, default=0)
    duels_total_away: Mapped[int] = mapped_column(Integer, default=0)
    duels_won_home: Mapped[int] = mapped_column(Integer, default=0)
    duels_won_away: Mapped[int] = mapped_column(Integer, default=0)
    dribbles_attempts_home: Mapped[int] = mapped_column(Integer, default=0)
    dribbles_attempts_away: Mapped[int] = mapped_column(Integer, default=0)
    dribbles_success_home: Mapped[int] = mapped_column(Integer, default=0)
    dribbles_success_away: Mapped[int] = mapped_column(Integer, default=0)
    tackles_total_home: Mapped[int] = mapped_column(Integer, default=0)
    tackles_total_away: Mapped[int] = mapped_column(Integer, default=0)
    interceptions_home: Mapped[int] = mapped_column(Integer, default=0)
    interceptions_away: Mapped[int] = mapped_column(Integer, default=0)
    passes_key_home: Mapped[int] = mapped_column(Integer, default=0)
    passes_key_away: Mapped[int] = mapped_column(Integer, default=0)
    fouls_committed_home: Mapped[int] = mapped_column(Integer, default=0)
    fouls_committed_away: Mapped[int] = mapped_column(Integer, default=0)
    fouls_drawn_home: Mapped[int] = mapped_column(Integer, default=0)
    fouls_drawn_away: Mapped[int] = mapped_column(Integer, default=0)

    # Os 3 jogadores mais bem avaliados de cada lado neste snapshot
    # (nome + nota + foto), guardados como JSON - nao faz sentido ter uma
    # coluna por jogador, e ter isso salvo a cada ciclo elimina a
    # necessidade do endpoint de detalhes fazer uma chamada de API na hora
    # toda vez que o usuario abre a tela (ver routers/matches.py).
    top_players_home: Mapped[list | None] = mapped_column(JSON, default=list)
    top_players_away: Mapped[list | None] = mapped_column(JSON, default=list)

    # False quando a API-Football ainda nao tinha dados de jogador para
    # essa partida no momento da coleta (comum nos primeiros minutos) -
    # o frontend mostra um aviso em vez de zeros enganosos.
    player_stats_available: Mapped[bool] = mapped_column(Boolean, default=True)
