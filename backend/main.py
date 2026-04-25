"""
Synapse Council v2.0 - FastAPI Application
Punto de entrada principal del backend
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.local_db import init_db

# Configurar logging básico para ver en consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Importar routers
from backend.api.routes.health import router as health_router
from backend.api.routes.sessions import router as sessions_router
from backend.api.routes.websockets import router as websockets_router
from backend.api.routes.network import router as network_router
from backend.api.routes.debate import router as debate_router
from backend.network.discovery import node_discoverer

# Configurar logging estructurado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()  # Cambiado de JSONRenderer para ver en consola
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager para startup/shutdown"""
    # Startup
    logger.info("synapse_council.starting", version="2.0.0", node_role=settings.NODE_ROLE)
    
    # Inicializar base de datos
    await init_db()
    logger.info("database.initialized", url=settings.DATABASE_URL)
    
    # Iniciar descubrimiento de red
    await node_discoverer.start()
    
    yield
    
    # Shutdown
    await node_discoverer.stop()
    logger.info("synapse_council.stopping")


app = FastAPI(
    title="Synapse Council v2.0",
    description="Plataforma de razonamiento colectivo híbrido con Tribunal de Magistrados",
    version="2.0.0",
    lifespan=lifespan,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de seguridad (Fase 5)
from backend.api.middleware import RateLimitMiddleware, SecurityHeadersMiddleware, LoggingMiddleware

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    burst_size=10
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)


# Registrar routers
app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(websockets_router)
app.include_router(network_router)
app.include_router(debate_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Endpoint raíz con información del sistema"""
    return {
        "name": "Synapse Council",
        "version": "2.0.0",
        "description": "Plataforma de razonamiento colectivo híbrido",
        "node_role": settings.NODE_ROLE,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
