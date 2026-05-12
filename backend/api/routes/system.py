"""
Synapse Council v3.0 - System API Routes
Endpoints para configuración, métricas, chat directo y wake-on-RDP
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
import psutil
import time

import structlog

from backend.config import get_settings
from backend.engine.agent_orchestrator import AgentOrchestrator, AgentConfig
from backend.services.rdp_manager import RDPManager, RDPSecurityError, RDPRateLimitError

logger = structlog.get_logger()

router = APIRouter(prefix="/system", tags=["System"])
settings = get_settings()
orchestrator = AgentOrchestrator()


LOCALHOSTS = {"127.0.0.1", "::1", "localhost"}


async def require_admin_access(request: Request) -> None:
    """
    Protects operational endpoints.
    If ADMIN_API_TOKEN is set, clients must send it in X-Admin-Token or Authorization: Bearer.
    If no token is set, only localhost clients are allowed by default.
    """
    configured_token = settings.ADMIN_API_TOKEN
    if configured_token:
        header_token = request.headers.get("X-Admin-Token")
        auth_header = request.headers.get("Authorization", "")
        bearer_token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else None

        if header_token != configured_token and bearer_token != configured_token:
            raise HTTPException(status_code=401, detail="Invalid admin token")
        return

    if settings.ADMIN_API_LOCALHOST_ONLY:
        client_host = request.client.host if request.client else ""
        if client_host not in LOCALHOSTS:
            raise HTTPException(
                status_code=403,
                detail="Admin API is restricted to localhost unless ADMIN_API_TOKEN is configured",
            )


class SettingsRequest(BaseModel):
    """Request para actualizar configuración"""
    openrouterKey: Optional[str] = None
    geminiKey: Optional[str] = None
    groqKey: Optional[str] = None
    deepseekKey: Optional[str] = None
    ollamaUrl: Optional[str] = None
    lmStudioUrl: Optional[str] = None
    janUrl: Optional[str] = None
    workerHost: Optional[str] = None
    workerOllamaPort: Optional[int] = None
    workerLmStudioPort: Optional[int] = None
    workerJanPort: Optional[int] = None
    discoveryPort: Optional[int] = None
    discoveryInterval: Optional[int] = None
    webAgentEnabled: Optional[bool] = None
    supabaseEnabled: Optional[bool] = None
    agentReputationEnabled: Optional[bool] = None


class DirectChatRequest(BaseModel):
    """Request para chat directo a modelo"""
    message: str
    model: str
    engine: str = "groq"
    temperature: float = 0.7
    max_tokens: int = 2048


class WakeWorkerRequest(BaseModel):
    """Request para despertar o conectar al Worker por RDP (manual)"""
    hostname: Optional[str] = Field(default=None, description="Hostname del Worker (usa config si no se proporciona)")
    username: Optional[str] = Field(default=None, description="Usuario RDP (usa config si no se proporciona)")
    password: Optional[str] = Field(default=None, description="Contraseña RDP (usa config si no se proporciona)")


@router.get("/settings", dependencies=[Depends(require_admin_access)])
async def get_settings_endpoint():
    """Obtiene configuración actual del sistema"""
    def _mask(key: str | None) -> str | None:
        return key[:8] + "..." if key else None

    return {
        # API Keys (enmascaradas por seguridad)
        "openrouterKey": _mask(settings.OPENROUTER_API_KEY),
        "geminiKey": _mask(settings.GEMINI_API_KEY),
        "groqKey": _mask(settings.GROQ_API_KEY),
        "deepseekKey": _mask(settings.DEEPSEEK_API_KEY),

        # Engine Configuration
        "ollamaUrl": settings.OLLAMA_BASE_URL,
        "lmStudioUrl": settings.LM_STUDIO_BASE_URL,
        "janUrl": settings.JAN_BASE_URL,

        # Worker Configuration
        "workerHost": settings.WORKER_HOST,
        "workerOllamaPort": settings.WORKER_OLLAMA_PORT,
        "workerLmStudioPort": settings.WORKER_LM_STUDIO_PORT,
        "workerJanPort": settings.WORKER_JAN_PORT,

        # Discovery
        "discoveryPort": settings.DISCOVERY_PORT,
        "discoveryInterval": settings.DISCOVERY_INTERVAL,

        # Features
        "webAgentEnabled": settings.WEB_AGENT_ENABLED,
        "supabaseEnabled": settings.SUPABASE_ENABLED,
        "agentReputationEnabled": settings.AGENT_REPUTATION_ENABLED,
    }


@router.post("/settings", dependencies=[Depends(require_admin_access)])
async def update_settings_endpoint(req: SettingsRequest):
    """Actualiza configuración del sistema"""
    # Nota: En una implementación real, esto debería actualizar el archivo .env
    # Por ahora, solo retornamos éxito
    return {"success": True, "message": "Settings updated (implementación pendiente)"}


@router.post("/chat/direct", dependencies=[Depends(require_admin_access)])
async def direct_chat_endpoint(req: DirectChatRequest):
    """
    Chat directo a un modelo específico (engines: groq, gemini, openrouter, deepseek).
    """
    system_prompt = "Eres un asistente útil. Responde de manera concisa y directa."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.message},
    ]

    try:
        response_parts: list[str] = []

        engine = req.engine.lower()

        if engine == "groq":
            if not settings.GROQ_API_KEY:
                raise HTTPException(status_code=503, detail="Groq API key not configured")
            from backend.adapters.groq import GroqClient
            client = GroqClient()
            async for token in client.chat_completion(
                model=req.model,
                messages=messages,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                stream=True,
            ):
                response_parts.append(token)

        elif engine == "gemini":
            if not settings.GEMINI_API_KEY:
                raise HTTPException(status_code=503, detail="Gemini API key not configured")
            from backend.adapters.gemini import GeminiClient
            client = GeminiClient()
            async for token in client.chat_completion(
                model=req.model,
                messages=messages,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                stream=True,
            ):
                response_parts.append(token)

        elif engine == "openrouter":
            if not settings.OPENROUTER_API_KEY:
                raise HTTPException(status_code=503, detail="OpenRouter API key not configured")
            from backend.adapters.openrouter import OpenRouterClient
            client = OpenRouterClient()
            async for token in client.chat_completion(
                model=req.model,
                messages=messages,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                stream=True,
            ):
                response_parts.append(token)

        elif engine == "deepseek":
            if not settings.DEEPSEEK_API_KEY:
                raise HTTPException(status_code=503, detail="DeepSeek API key not configured")
            from backend.adapters.deepseek import DeepSeekClient
            client = DeepSeekClient()
            async for token in client.chat_completion(
                model=req.model,
                messages=messages,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                stream=True,
            ):
                response_parts.append(token)

        elif engine == "web_agent":
            from backend.adapters.web_agent import WebAgentClient, SITE_CONFIGS
            if req.model not in SITE_CONFIGS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Web Agent site '{req.model}' not supported. Use: {', '.join(SITE_CONFIGS.keys())}",
                )
            client = WebAgentClient()
            response_text = await client.query(req.model, req.message)
            response_parts.append(response_text)

        else:
            supported = "groq, gemini, openrouter, deepseek, web_agent"
            raise HTTPException(
                status_code=400,
                detail=f"Engine '{req.engine}' not supported. Use: {supported}",
            )

        return {
            "response": "".join(response_parts),
            "model": req.model,
            "engine": req.engine,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_metrics_endpoint():
    """Obtiene métricas del sistema"""
    # Métricas de CPU y memoria
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    # Métricas de debates (deberían venir de los controllers)
    # Por ahora retornamos valores simulados
    return {
        "activeDebates": 0,
        "totalTokens": 0,
        "avgLatency": 0,
        "cpuUsage": cpu_percent,
        "memoryUsage": memory.percent
    }


@router.get("/health")
async def health_check_endpoint():
    """Health check del sistema"""
    from backend.main import heartbeat_manager
    
    worker_connected = False
    worker_ip = None
    last_heartbeat = None
    
    if heartbeat_manager:
        worker_connected = heartbeat_manager.is_alive()
        worker_ip = heartbeat_manager.get_peer_ip()
        last_heartbeat = heartbeat_manager.get_last_heartbeat_time()
        if last_heartbeat:
            last_heartbeat = last_heartbeat.isoformat()
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "worker_connected": worker_connected,
        "worker_ip": worker_ip,
        "last_heartbeat": last_heartbeat,
        "transfer_speed": 0.0  # Debería medirse realmente
    }


@router.post("/wake-worker", dependencies=[Depends(require_admin_access)])
async def wake_worker_endpoint(req: WakeWorkerRequest, request: Request):
    """
    Abre escritorio remoto hacia el Worker (RDP manual).
    
    - Si no se proporcionan credenciales, usa las de configuración (.env)
    - Rate limit: 1 llamada cada 60 segundos por IP
    - Solo funciona en Windows (requiere mstsc.exe)
    """
    # Usar configuración del sistema si no se proporcionan credenciales
    hostname = req.hostname or settings.RDP_WORKER_HOSTNAME
    username = req.username or settings.RDP_WORKER_USERNAME
    password = req.password or settings.RDP_WORKER_PASSWORD
    
    # Rate limiting por IP del cliente
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        result = await RDPManager.connect_to_worker_async(
            hostname=hostname,
            username=username,
            password=password,
            rate_limit_id=client_ip
        )
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.message)
        
        return {
            "success": True,
            "message": result.message,
            "ip": result.ip,
            "duration_ms": result.duration_ms,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None
        }
        
    except RDPSecurityError as e:
        raise HTTPException(status_code=400, detail=f"Error de seguridad: {str(e)}")
    except RDPRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))


@router.post("/wake-worker-auto", dependencies=[Depends(require_admin_access)])
async def wake_worker_auto_endpoint(request: Request):
    """
    Wake automático del Worker usando credenciales de configuración.
    
    - Usa RDP_WORKER_HOSTNAME, RDP_WORKER_USERNAME, RDP_WORKER_PASSWORD de .env
    - Rate limit global: 1 llamada cada 60 segundos
    - Ideal para llamadas automáticas desde SequentialDebateController
    """
    if not settings.RDP_ENABLED:
        raise HTTPException(status_code=503, detail="RDP deshabilitado en configuración")
    
    try:
        # Usar método async directamente (no asyncio.run())
        result = await RDPManager.connect_to_worker_async(
            hostname=settings.RDP_WORKER_HOSTNAME,
            username=settings.RDP_WORKER_USERNAME,
            password=settings.RDP_WORKER_PASSWORD,
            rate_limit_id="auto_wake"
        )
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.message)
        
        return {
            "success": True,
            "message": result.message,
            "hostname": settings.RDP_WORKER_HOSTNAME,
            "ip": result.ip,
            "duration_ms": result.duration_ms,
            "config_source": "environment",
            "timestamp": result.timestamp.isoformat() if result.timestamp else None
        }
        
    except RDPRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")


@router.get("/rdp-status", dependencies=[Depends(require_admin_access)])
async def rdp_status_endpoint():
    """Obtiene estado de configuración RDP (sin exponer credenciales)"""
    return {
        "enabled": settings.RDP_ENABLED,
        "hostname": settings.RDP_WORKER_HOSTNAME,
        "username": settings.RDP_WORKER_USERNAME.split("\\")[-1] if "\\" in settings.RDP_WORKER_USERNAME else settings.RDP_WORKER_USERNAME,
        "domain": settings.RDP_WORKER_USERNAME.split("\\")[0] if "\\" in settings.RDP_WORKER_USERNAME else None,
        "rate_limit_seconds": settings.RDP_RATE_LIMIT_SECONDS,
        "password_configured": bool(settings.RDP_WORKER_PASSWORD),
        "platform": "windows_only"
    }


# ─── Worker Services Management ──────────────────────────────────────

class WorkerServicesResponse(BaseModel):
    services: dict
    worker_ip: Optional[str] = None


class WorkerLaunchRequest(BaseModel):
    service: str  # ollama, lm_studio, jan, all


@router.get("/worker/services",
            dependencies=[Depends(require_admin_access)])
async def get_worker_services():
    """Obtiene estado de todos los servicios en el Worker"""
    try:
        from backend.engine.worker_launcher import worker_service_manager
        host = await worker_service_manager.resolve_worker_ip()
        services = await worker_service_manager.check_all_services()
        summary = worker_service_manager.get_status_summary(services)
        logger.info("worker.services_checked", summary=summary.replace("\n", " | "))
        return {
            "worker_ip": host,
            "services": services,
            "summary": summary,
        }
    except ImportError:
        return {"error": "WorkerServiceManager no disponible"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/worker/services/launch",
             dependencies=[Depends(require_admin_access)])
async def launch_worker_service(req: WorkerLaunchRequest):
    """Lanza un servicio específico en el Worker"""
    try:
        from backend.engine.worker_launcher import worker_service_manager

        if req.service == "all":
            results = await worker_service_manager.ensure_all_services()
        else:
            result = await worker_service_manager.ensure_service_running(req.service)
            results = {req.service: result}

        return {
            "success": all(r.get("success") for r in results.values()),
            "results": results,
        }
    except ImportError:
        return {"error": "WorkerServiceManager no disponible"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
