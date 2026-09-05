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


async def init_db() -> None:
    """Cria as tabelas caso ainda nao existam (idempotente)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
