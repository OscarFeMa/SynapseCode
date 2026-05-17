"""
Debug Routes - Endpoints de diagnóstico del sistema.
Sin impacto en funcionalidad principal.
"""

import time
from typing import Any

import structlog
from fastapi import APIRouter

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/debug")


@router.get("/system")
async def system_debug() -> dict[str, Any]:
    """
    Estado de circuit breakers y motores.
    Útil para diagnóstico de problemas sin revisar logs.
    """
    try:
        # Importar localmente para evitar circular imports
        from backend.engine.local_engine_manager import EngineType, LocalEngineManager

        lm = LocalEngineManager()
        current_time = time.time()

        # Construir estado de circuit breakers
        circuit_breakers = {}
        for engine_type in EngineType:
            broken_until = lm.circuit_broken_until.get(engine_type, 0)
            is_open = broken_until > current_time
            seconds_remaining = max(0, int(broken_until - current_time)) if is_open else 0

            circuit_breakers[engine_type.value] = {
                "open": is_open,
                "seconds_remaining": seconds_remaining,
                "failure_count": lm.engine_failures.get(engine_type, 0),
            }

        # Construir estado de salud
        engine_health = {k.value: v for k, v in lm.engine_health.items()}

        return {
            "status": "ok",
            "circuit_breakers": circuit_breakers,
            "engine_health": engine_health,
            "timestamp": int(current_time),
        }

    except Exception as e:
        logger.error("debug.system_error", error=str(e))
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve system debug info",
        }


@router.get("/health-detailed")
async def health_detailed() -> dict[str, Any]:
    """
    Health check detallado con información adicional.
    """
    try:
        from sqlalchemy import text

        from backend.database.local_db import engine as db_engine

        # Check database
        db_status = "unknown"
        try:
            with db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                db_status = "ok"
        except Exception as db_error:
            db_status = f"error: {db_error!s}"

        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "components": {
                "database": db_status,
            },
            "timestamp": int(time.time()),
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/config")
async def debug_config() -> dict[str, Any]:
    """
    Configuración no sensible del sistema.
    """
    try:
        from backend.config import settings

        return {
            "status": "ok",
            "config": {
                "node_role": settings.NODE_ROLE,
                "master_host": settings.MASTER_HOST,
                "worker_host": settings.WORKER_HOST,
                "ollama_base_url": settings.OLLAMA_BASE_URL,
                "supabase_enabled": bool(settings.SUPABASE_URL),
                "reputation_enabled": getattr(settings, "AGENT_REPUTATION_ENABLED", False),
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
