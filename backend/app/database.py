"""
Camada de acesso ao banco de dados (SQLAlchemy 2.0 assincrono).

Usa SQLite por padrao (zero configuracao para rodar localmente), mas como
tudo passa por SQLAlchemy Core/ORM, trocar para Postgres em producao e
apenas uma questao de mudar DATABASE_URL no .env - nenhum codigo de
modelo/servico precisa mudar.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


# Colunas adicionadas depois ao MatchSnapshot (ver app/models/snapshot.py)
# para a tela detalhada de "Partidas Ao Vivo". `Base.metadata.create_all`
# so cria TABELAS que ainda nao existem - nunca adiciona colunas novas a
# uma tabela ja existente. Como e um app pessoal com um unico banco
# SQLite, uma ferramenta de migracao (Alembic) seria exagero: em vez
# disso, checamos manualmente o que falta e adicionamos via ALTER TABLE.
_SNAPSHOT_NEW_COLUMNS: dict[str, str] = {
    "shots_blocked_home": "INTEGER DEFAULT 0",
    "shots_blocked_away": "INTEGER DEFAULT 0",
    "shots_inside_box_home": "INTEGER DEFAULT 0",
    "shots_inside_box_away": "INTEGER DEFAULT 0",
    "shots_outside_box_home": "INTEGER DEFAULT 0",
    "shots_outside_box_away": "INTEGER DEFAULT 0",
    "passes_total_home": "INTEGER DEFAULT 0",
    "passes_total_away": "INTEGER DEFAULT 0",
    "passes_accurate_home": "INTEGER DEFAULT 0",
    "passes_accurate_away": "INTEGER DEFAULT 0",
    "passes_pct_home": "FLOAT DEFAULT 0",
    "passes_pct_away": "FLOAT DEFAULT 0",
    "goalkeeper_saves_home": "INTEGER DEFAULT 0",
    "goalkeeper_saves_away": "INTEGER DEFAULT 0",
    "xg_home": "FLOAT DEFAULT 0",
    "xg_away": "FLOAT DEFAULT 0",
    # Agregados de jogador que o collect_snapshots passou a coletar a cada
    # ciclo (ver app/models/snapshot.py e app/services/collector.py).
    "duels_total_home": "INTEGER DEFAULT 0",
    "duels_total_away": "INTEGER DEFAULT 0",
    "duels_won_home": "INTEGER DEFAULT 0",
    "duels_won_away": "INTEGER DEFAULT 0",
    "dribbles_attempts_home": "INTEGER DEFAULT 0",
    "dribbles_attempts_away": "INTEGER DEFAULT 0",
    "dribbles_success_home": "INTEGER DEFAULT 0",
    "dribbles_success_away": "INTEGER DEFAULT 0",
    "tackles_total_home": "INTEGER DEFAULT 0",
    "tackles_total_away": "INTEGER DEFAULT 0",
    "interceptions_home": "INTEGER DEFAULT 0",
    "interceptions_away": "INTEGER DEFAULT 0",
    "passes_key_home": "INTEGER DEFAULT 0",
    "passes_key_away": "INTEGER DEFAULT 0",
    "fouls_committed_home": "INTEGER DEFAULT 0",
    "fouls_committed_away": "INTEGER DEFAULT 0",
    "fouls_drawn_home": "INTEGER DEFAULT 0",
    "fouls_drawn_away": "INTEGER DEFAULT 0",
    "top_players_home": "TEXT",
    "top_players_away": "TEXT",
    "player_stats_available": "INTEGER DEFAULT 1",
}


async def _ensure_snapshot_columns(conn) -> None:
    """Adiciona ao banco SQLite ja existente qualquer coluna nova do
    MatchSnapshot que ainda nao exista - roda toda vez que o backend sobe,
    mas e idempotente (so mexe no que realmente falta)."""
    if not settings.database_url.startswith("sqlite"):
        return  # Postgres/outros: usar uma ferramenta de migracao de verdade.

    result = await conn.exec_driver_sql("PRAGMA table_info(match_snapshots)")
    existing_columns = {row[1] for row in result.fetchall()}
    for column, ddl_type in _SNAPSHOT_NEW_COLUMNS.items():
        if column not in existing_columns:
            await conn.exec_driver_sql(f"ALTER TABLE match_snapshots ADD COLUMN {column} {ddl_type}")


async def init_db() -> None:
    """Cria as tabelas caso ainda nao existam (idempotente)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_snapshot_columns(conn)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
