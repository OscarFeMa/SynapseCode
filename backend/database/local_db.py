"""
Synapse Council v2.0 - Local Database
Engine y sesion async SQLite con aiosqlite
"""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import get_settings
from backend.database.migrations.sqlite_migrations import run_sqlite_migrations
from backend.database.models import Base

settings = get_settings()

# Crear engine async con timeout para escrituras concurrentes
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"timeout": 20, "check_same_thread": False},
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    """
    Activa WAL mode para permitir escrituras concurrentes sin bloqueos.
    PRAGMA journal_mode=WAL: multiples lectores + 1 escritor simultaneo
    PRAGMA synchronous=NORMAL: balance rendimiento/seguridad
    PRAGMA busy_timeout=20000: espera 20s antes de lanzar OperationalError
    PRAGMA cache_size=-64000: 64MB cache en memoria
    PRAGMA temp_store=MEMORY: tablas temporales en RAM
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=20000")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


# Crear session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    """Dependency para obtener sesión de DB en endpoints"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Inicializa la base de datos creando todas las tablas"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(run_sqlite_migrations)


async def drop_db():
    """Elimina todas las tablas (útil para tests)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
