from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TeamMatchHistory(Base):
    """
    Cache dos ultimos jogos FINALIZADOS de um time (adversario, mando de
    campo, competicao, placar e placar do intervalo) - usado pela tela
    "Comparativo Histórico" (forma dos times). Ao contrario de TeamForm
    (que ja guarda so as MEDIAS agregadas de uma amostra fixa, usada pelo
    motor de recomendacao), aqui guardamos uma linha POR JOGO - os filtros
    de "quantos jogos", "so em casa/fora" e "so na mesma competicao" sao
    recalculados no FRONTEND em cima dessas linhas, sem chamada nova a API
    a cada mudanca de filtro (ver app/services/team_history_service.py).

    Cada refresh APAGA e recria todas as linhas do time (nunca mais que
    MAX_HISTORY_GAMES por vez) - mais simples que fazer upsert por jogo, e
    a tabela e pequena o bastante (no maximo MAX_HISTORY_GAMES linhas por
    time) pra isso nao ser um problema de performance.
    """

    __tablename__ = "team_match_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)

    fixture_api_id: Mapped[int] = mapped_column(Integer, index=True)
    opponent_name: Mapped[str] = mapped_column(String(120), default="")
    is_home: Mapped[bool] = mapped_column(Boolean, default=True)
    league_api_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    league_name: Mapped[str] = mapped_column(String(120), default="")
    played_at: Mapped[datetime] = mapped_column(DateTime)

    goals_for: Mapped[int] = mapped_column(Integer, default=0)
    goals_against: Mapped[int] = mapped_column(Integer, default=0)
    # None quando a API nao devolveu score.halftime pra esse jogo (raro,
    # mas mais seguro que assumir 0 x 0 - ver stats do intervalo no
    # frontend, que pulam o jogo quando qualquer um dos dois for None).
    ht_goals_for: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ht_goals_against: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Quando esse LOTE (todas as linhas desse time, recriadas juntas) foi
    # buscado - usado pra decidir se o cache esta velho (ver
    # team_history_service.py). Nao usa `played_at` do jogo mais recente
    # pra isso: um time sem jogo ha varios dias pareceria sempre "velho" e
    # forcaria refetch a toda hora, mesmo com o cache perfeitamente valido.
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
