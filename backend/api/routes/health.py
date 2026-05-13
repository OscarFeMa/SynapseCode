"""
Synapse Council v2.0 - Health Routes
"""
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import structlog
from sqlalchemy import text

from backend.config import get_settings
from backend.adapters.ollama import OllamaClient
from backend.adapters.lm_studio import LMStudioClient
from backend.adapters.jan import JanClient
from backend.adapters.openrouter import OpenRouterClient
from backend.adapters.web_agent import WebAgentClient
from backend.database.local_db import engine

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter()


async def check_database_health() -> Dict[str, Any]:
    """Verifica que la base de datos local acepta consultas."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "url": settings.DATABASE_URL}
    except Exception as e:
        return {"status": "unavailable", "url": settings.DATABASE_URL, "error": str(e)}

async def check_service_health(client_class, settings_prefix: str) -> Dict[str, Any]:
    """Verifica el estado de un servicio de IA"""
    try:
        if settings_prefix == "ollama":
            client = OllamaClient(base_url=settings.worker_ollama_url)
        elif settings_prefix == "lm_studio":
            client = LMStudioClient(base_url=settings.worker_lm_studio_url)
        elif settings_prefix == "jan":
            client = JanClient(base_url=settings.worker_jan_url)
        elif settings_prefix == "openrouter":
            if not settings.OPENROUTER_ENABLED or not settings.OPENROUTER_API_KEY:
                return {"status": "skipped", "reason": "OpenRouter is disabled or not configured"}
            client = OpenRouterClient(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL
            )
        elif settings_prefix == "web_agent":
            client = WebAgentClient(
                enabled=settings.WEB_AGENT_ENABLED,
                browser=settings.WEB_AGENT_BROWSER,
                headless=settings.WEB_AGENT_HEADLESS,
            )
        elif settings_prefix == "huggingface":
            if not settings.HF_ENABLED or not settings.HF_TOKEN:
                return {"status": "skipped", "reason": "HF_TOKEN not configured"}
            from backend.adapters.huggingface import HuggingFaceClient
            client = HuggingFaceClient(api_key=settings.HF_TOKEN)
        else:
            return {"status": "unknown", "error": "Unknown service"}
        
        result = await client.health_check()
        return result
    except Exception as e:
        error_msg = str(e)
        suggested = _get_suggested_fix(settings_prefix, error_msg)
        return {
            "status": "unavailable",
            "error": error_msg,
            "suggested_fix": suggested
        }


def _get_suggested_fix(service: str, error: str) -> str:
    """Sugiere soluciones para errores comunes por servicio"""
    fixes = {
        "ollama": "Verifica que Ollama este corriendo en el Worker: 'ollama serve'. Worker IP: " + str(settings.get_worker_host()),
        "lm_studio": "Abre LM Studio en el Worker y activa Local Inference Server",
        "jan": "Abre Jan en el Worker y activa el servidor API",
        "openrouter": "La API key no tiene credito. Agrega minimo $1 en https://openrouter.ai/settings/credits",
        "web_agent": "Ejecuta: playwright install chromium",
        "huggingface": "Obtener token en https://huggingface.co/settings/tokens",
    }
    
    if service in fixes:
        return fixes[service]
    
    if "Cannot connect" in error or "Connection refused" in error.lower():
        return "Verifica que el servicio este corriendo y sea accesible desde la red"
    if "timeout" in error.lower():
        return "El servicio no responde. Verifica conectividad de red"
    if "401" in error or "Unauthorized" in error:
        return "API key invalida. Verifica tus credenciales en .env"
    if "402" in error or "Payment Required" in error:
        return "Saldo insuficiente. Agrega credito a tu cuenta"
    if "429" in error or "Rate Limit" in error:
        return "Limite de tasa excedido. Espera 1 minuto y reintenta"
    
    return "Revisa los logs del servidor para mas detalles"


async def collect_dependency_health() -> Dict[str, Any]:
    """
    Recolecta salud detallada de dependencias.
    No debe usarse como liveness check porque toca servicios externos.
    """
    start_time = asyncio.get_event_loop().time()
    
    # Verificar todos los servicios en paralelo
    results = await asyncio.gather(
        check_database_health(),
        check_service_health(OllamaClient, "ollama"),
        check_service_health(LMStudioClient, "lm_studio"),
        check_service_health(JanClient, "jan"),
        check_service_health(OpenRouterClient, "openrouter"),
        check_service_health(WebAgentClient, "web_agent"),
        check_service_health(None, "huggingface"),
        return_exceptions=True
    )
    
    database_health, ollama_health, lm_studio_health, jan_health, openrouter_health, web_agent_health, huggingface_health = results
    
    # Determinar estado general
    services_status = {
        "database": database_health.get("status", "unknown") if isinstance(database_health, dict) else "error",
        "ollama": ollama_health.get("status", "unknown") if isinstance(ollama_health, dict) else "error",
        "lm_studio": lm_studio_health.get("status", "unknown") if isinstance(lm_studio_health, dict) else "error",
        "jan": jan_health.get("status", "unknown") if isinstance(jan_health, dict) else "error",
        "openrouter": openrouter_health.get("status", "unknown") if isinstance(openrouter_health, dict) else "error",
        "web_agent": web_agent_health.get("status", "unknown") if isinstance(web_agent_health, dict) else "error",
        "huggingface": huggingface_health.get("status", "unknown") if isinstance(huggingface_health, dict) else "error",
    }
    
    critical_services = ["database"]
    is_healthy = all(
        services_status[s] in ["healthy", "online", "available"]
        for s in critical_services
    )
    
    elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
    
    response = {
        "status": "healthy" if is_healthy else "degraded",
        "version": "2.0.0",
        "node_role": settings.NODE_ROLE,
        "timestamp": asyncio.get_event_loop().time(),
        "check_duration_ms": elapsed_ms,
        "services": {
            "database": database_health if isinstance(database_health, dict) else {"status": "error", "error": str(database_health)},
            "ollama": ollama_health if isinstance(ollama_health, dict) else {"status": "error", "error": str(ollama_health)},
            "lm_studio": lm_studio_health if isinstance(lm_studio_health, dict) else {"status": "error", "error": str(lm_studio_health)},
            "jan": jan_health if isinstance(jan_health, dict) else {"status": "error", "error": str(jan_health)},
            "openrouter": openrouter_health if isinstance(openrouter_health, dict) else {"status": "error", "error": str(openrouter_health)},
            "web_agent": web_agent_health if isinstance(web_agent_health, dict) else {"status": "error", "error": str(web_agent_health)},
            "huggingface": huggingface_health if isinstance(huggingface_health, dict) else {"status": "error", "error": str(huggingface_health)},
        }
    }
    
    logger.info("health_check.completed", 
                overall_status=response["status"], 
                duration_ms=elapsed_ms)
    
    return response


@router.get("/health/live")
async def live_check() -> Dict[str, Any]:
    """Liveness check: solo confirma que el proceso FastAPI responde."""
    return {
        "status": "alive",
        "version": "2.0.0",
        "node_role": settings.NODE_ROLE,
        "timestamp": asyncio.get_event_loop().time(),
    }


@router.get("/health/ready")
async def ready_check() -> Dict[str, Any]:
    """Readiness check: valida dependencias minimas para aceptar trafico."""
    database_health = await check_database_health()
    if database_health.get("status") not in ["healthy", "online", "available"]:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "database": database_health})

    return {
        "status": "ready",
        "version": "2.0.0",
        "node_role": settings.NODE_ROLE,
        "services": {"database": database_health},
        "timestamp": asyncio.get_event_loop().time(),
    }


@router.get("/health/dependencies")
async def dependency_check() -> Dict[str, Any]:
    """Health check detallado de dependencias internas y externas."""
    return await collect_dependency_health()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check completo mantenido por compatibilidad.
    Para automatizaciones use /health/live o /health/ready.
    """
    return await collect_dependency_health()
