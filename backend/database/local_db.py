"""
Synapse Council v2.0 - Local Database
Engine y sesión async SQLite con aiosqlite
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.database.models import Base
from backend.config import get_settings

settings = get_settings()

# Crear engine async
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Cambiar a True para debug
    future=True,
)

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


async def drop_db():
    """Elimina todas las tablas (útil para tests)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
