"""
Synapse Council v2.0 - FastAPI Application
Punto de entrada principal del backend
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from backend.config import get_settings
from backend.database.local_db import init_db

# Configurar logging básico para ver en consola
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Importar routers
from backend.adapters.http_client_manager import HTTPClientManager
from backend.api.routes.cache import router as cache_router
from backend.api.routes.debate import router as debate_router
from backend.api.routes.health import router as health_router
from backend.api.routes.network import router as network_router
from backend.api.routes.runs import router as runs_router
from backend.api.routes.sessions import router as sessions_router
from backend.api.routes.system import router as system_router
from backend.api.routes.websockets import router as websockets_router
from backend.engine.task_manager import task_manager
from backend.monitoring.prometheus import render_prometheus_metrics
from backend.network.discovery import node_discoverer
from backend.network.heartbeat import HeartbeatManager
from backend.network.tcp_handshake import TCPHandshake

logger = structlog.get_logger()
settings = get_settings()

# Configurar logging estructurado con archivos rotatorios
from backend.logging_config import setup_logging

setup_logging(
    log_level=settings.LOG_LEVEL,
    log_dir=Path(settings.LOG_DIR),
    max_bytes=settings.LOG_MAX_BYTES,
    backup_count=settings.LOG_BACKUP_COUNT,
    console=True,
    file_output=settings.LOG_TO_FILE,
)

# Instancia global de heartbeat manager
heartbeat_manager: HeartbeatManager = None
tcp_handshake: TCPHandshake = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager para startup/shutdown"""
    global heartbeat_manager, tcp_handshake

    # Startup
    logger.info(
        "synapse_council.starting", version="2.0.0", node_role=settings.NODE_ROLE
    )

    # Inicializar base de datos
    await init_db()
    logger.info("database.initialized", url=settings.DATABASE_URL)

    # Iniciar task manager para background tasks
    await task_manager.start()
    logger.info("task_manager.started")

    # Iniciar memoria híbrida v2 (condicional)
    try:
        from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2

        hybrid_mem = get_hybrid_memory_v2()
        await hybrid_mem.start()
        logger.info("hybrid_memory_v2.started")
    except Exception as e:
        logger.warning("hybrid_memory_v2.start_failed", error=str(e))

    # Verificar y lanzar servicios del Worker al iniciar (v2.2+)
    # Verificar servicios esenciales del Worker al iniciar (solo Ollama y LM Studio)
    if settings.is_master and settings.RDP_ENABLED:
        try:
            from backend.engine.worker_launcher import worker_service_manager

            logger.info("worker.checking_services_on_startup")
            status = await worker_service_manager.check_all_services()
            for name in ["ollama", "lm_studio"]:
                svc = status.get(name, {})
                if svc.get("status") != "running":
                    logger.info(f"worker.{name}_offline_attempting_launch")
                    # Intentar solo RDP (WinRM no disponible), con timeout corto
                    import asyncio

                    try:
                        r = await asyncio.wait_for(
                            worker_service_manager.launch_service_rdp(name), timeout=5
                        )
                        logger.info(
                            f"worker.{name}_launch_result", success=r.get("success")
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"worker.{name}_launch_timeout")
                else:
                    logger.info(f"worker.{name}_already_running")
        except Exception as e:
            logger.warning("worker.startup_check_failed", error=str(e))

    # Iniciar descubrimiento de red
    await node_discoverer.start()

    # Iniciar TCP handshake (basado en Pensamiento Coral)
    tcp_handshake = TCPHandshake(role=settings.NODE_ROLE)

    # Iniciar heartbeat (basado en Pensamiento Coral)
    if settings.is_master:
        heartbeat_manager = HeartbeatManager(
            role="MASTER",
            interval=settings.HEARTBEAT_INTERVAL,
            timeout=settings.HEARTBEAT_TIMEOUT,
        )
        heartbeat_manager.start()
        logger.info("heartbeat.started", role="MASTER")
    else:
        # Worker inicia heartbeat cuando conoce la IP del Master
        heartbeat_manager = HeartbeatManager(
            role="WORKER",
            interval=settings.HEARTBEAT_INTERVAL,
            timeout=settings.HEARTBEAT_TIMEOUT,
        )
        logger.info("heartbeat.initialized", role="WORKER")

    yield

    # Shutdown
    await node_discoverer.stop()

    # Detener heartbeat
    if heartbeat_manager:
        heartbeat_manager.stop()
        logger.info("heartbeat.stopped")

    # Cerrar TCP handshake
    if tcp_handshake:
        tcp_handshake.close()
        logger.info("tcp_handshake.closed")

    # Detener memoria híbrida
    try:
        from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2

        hybrid_mem = get_hybrid_memory_v2()
        await hybrid_mem.stop()
        logger.info("hybrid_memory_v2.stopped")
    except Exception as e:
        logger.warning("hybrid_memory_v2.stop_failed", error=str(e))

    # Cerrar todas las conexiones HTTP
    await HTTPClientManager.close_all()
    logger.info("http_clients.closed")

    # Detener task manager
    await task_manager.shutdown()
    logger.info("task_manager.shutdown")

    logger.info("synapse_council.stopping")


app = FastAPI(
    title="Synapse Council v2.0",
    description="Plataforma de razonamiento colectivo híbrido con Tribunal de Magistrados",
    version="2.0.0",
    lifespan=lifespan,
)

# Middleware de seguridad (Fase 5)
from backend.api.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)

app.add_middleware(RateLimitMiddleware, requests_per_minute=120, burst_size=60)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

# Configurar CORS (Debe ser el último en añadirse para ser el primero en procesar/último en salir)
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True if "*" not in origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(websockets_router)
app.include_router(network_router)
app.include_router(debate_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")
app.include_router(cache_router, prefix="/api/v1/cache")

# Debug router (importación local para evitar imports circulares)
from backend.api.routes.debug import router as debug_router

app.include_router(debug_router)
logger.info("debug_router.enabled")


@app.get("/")
async def root():
    """Endpoint raíz con información del sistema"""
    return {
        "name": "Synapse Council",
        "version": "2.0.0",
        "description": "Plataforma de razonamiento colectivo híbrido",
        "node_role": settings.NODE_ROLE,
        "docs": "/docs",
        "health": "/health",
        "admin": "/admin",
    }


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Endpoint Prometheus para scraping."""
    return PlainTextResponse(
        content=render_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/admin", include_in_schema=False)
async def admin_panel():
    """Panel de administración web"""
    import os

    from fastapi.responses import FileResponse, HTMLResponse

    admin_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return HTMLResponse("<h1>Admin panel no encontrado</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=1,
    )
