"""
SynapseCode - Cache Management API
Endpoints para administrar la caché semántica
"""

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.caching.semantic_cache import semantic_cache

logger = structlog.get_logger()
router = APIRouter()


class CacheStatsResponse(BaseModel):
    """Modelo de respuesta para estadísticas de caché"""

    total_entries: int
    total_hits: int
    entries_with_embeddings: int
    hit_rate: float
    enabled: bool
    similarity_threshold: float
    ttl_hours: int


class CacheInvalidateRequest(BaseModel):
    """Modelo de solicitud para invalidar caché"""

    model: str | None = None
    engine: str | None = None


class CacheInvalidateResponse(BaseModel):
    """Modelo de respuesta para invalidación de caché"""

    count: int
    message: str


class CacheCleanupResponse(BaseModel):
    """Modelo de respuesta para limpieza de caché"""

    count: int
    message: str


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats() -> CacheStatsResponse:
    """
    Obtiene estadísticas de la caché semántica.
    """
    try:
        stats = await semantic_cache.get_stats()
        return CacheStatsResponse(**stats)
    except Exception as e:
        logger.error("cache.stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {e!s}")


@router.post("/invalidate", response_model=CacheInvalidateResponse)
async def invalidate_cache(request: CacheInvalidateRequest) -> CacheInvalidateResponse:
    """
    Invalida entradas de caché por modelo/engine.
    Si no se especifica modelo/engine, invalida todas las entradas.
    """
    try:
        count = await semantic_cache.invalidate(model=request.model, engine=request.engine)
        message = f"Invalidated {count} cache entries"
        if request.model:
            message += f" for model {request.model}"
        if request.engine:
            message += f" on engine {request.engine}"
        return CacheInvalidateResponse(count=count, message=message)
    except Exception as e:
        logger.error("cache.invalidate_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to invalidate cache: {e!s}")


@router.post("/cleanup", response_model=CacheCleanupResponse)
async def cleanup_cache() -> CacheCleanupResponse:
    """
    Elimina entradas expiradas de caché.
    """
    try:
        count = await semantic_cache.cleanup_expired()
        return CacheCleanupResponse(count=count, message=f"Cleaned up {count} expired cache entries")
    except Exception as e:
        logger.error("cache.cleanup_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cleanup cache: {e!s}")


@router.get("/health")
async def cache_health() -> dict[str, Any]:
    """
    Health check del servicio de caché.
    """
    try:
        stats = await semantic_cache.get_stats()
        return {
            "status": "healthy" if stats.get("enabled") else "disabled",
            "stats": stats,
        }
    except Exception as e:
        logger.error("cache.health_failed", error=str(e))
        return {"status": "error", "error": str(e)}
