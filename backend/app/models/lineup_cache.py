from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FixtureLineupCache(Base):
    """
    Cache da escalacao provavel/titular, tecnicos, arbitro e lesoes de uma
    partida - usado pela tela "Escalações". Ao contrario dos snapshots
    (que mudam a cada 5min durante o jogo), essa informacao e publicada
    pela API-Football uns 60min antes do apito inicial e NAO muda mais
    depois - por isso um cache com validade de horas (ver
    app/services/lineup_service.py) em vez de recalcular a cada ciclo.

    Uma linha por partida (fixture_id e unico) - sempre atualizada no
    lugar (nunca apagada/recriada como TeamMatchHistory), porque so existe
    uma escalacao por partida, nao uma lista que cresce.
    """

    __tablename__ = "fixture_lineup_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), unique=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # None = API-Football nao informou (fixture.referee vem null em varias
    # ligas menores) - nunca inventamos um nome.
    referee: Mapped[str | None] = mapped_column(String(200), nullable=True)

    formation_home: Mapped[str | None] = mapped_column(String(20), nullable=True)
    formation_away: Mapped[str | None] = mapped_column(String(20), nullable=True)
    coach_home: Mapped[str | None] = mapped_column(String(120), nullable=True)
    coach_away: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Cada item: {"number": int, "name": str, "pos": "G"/"D"/"M"/"F", "grid": "linha:posicao" ou None}.
    # NAO inclui nota do jogador nem foto - a API-Football nao fornece nota
    # pre-jogo (isso e de outro provedor), e a foto exigiria uma chamada
    # extra por jogador (custo alto demais so pra um icone).
    lineup_home: Mapped[list] = mapped_column(JSON, default=list)
    lineup_away: Mapped[list] = mapped_column(JSON, default=list)
    substitutes_home: Mapped[list] = mapped_column(JSON, default=list)
    substitutes_away: Mapped[list] = mapped_column(JSON, default=list)

    # Cada item: {"player_name": str, "reason": str, "type": str}. Endpoint
    # separado da API-Football (/injuries) - cobertura varia por liga, uma
    # lista vazia e normal, nao um erro (ver lineup_service.py).
    injuries_home: Mapped[list] = mapped_column(JSON, default=list)
    injuries_away: Mapped[list] = mapped_column(JSON, default=list)
