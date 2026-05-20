"""
Synapse Council v3.0 - System API Routes
Endpoints para configuración, métricas, chat directo y wake-on-RDP
"""

import subprocess
import time
from datetime import datetime

import psutil
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select

from backend.config import get_settings
from backend.database.local_db import AsyncSessionLocal
from backend.database.models import (
    AbsurdumProof,
    DailyMetricsSnapshot,
    ModelPerformance,
    ReductioAbsurdumProof,
    SequentialDebate,
    SupabaseSyncQueueItem,
    TopicTrending,
)
from backend.engine.agent_orchestrator import AgentOrchestrator
from backend.engine.tribunal_config import build_tribunal_config
from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2
from backend.services.rdp_manager import RDPManager, RDPRateLimitError, RDPSecurityError

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

    openrouterKey: str | None = None
    geminiKey: str | None = None
    groqKey: str | None = None
    deepseekKey: str | None = None
    ollamaUrl: str | None = None
    lmStudioUrl: str | None = None
    janUrl: str | None = None
    workerHost: str | None = None
    workerOllamaPort: int | None = None
    workerLmStudioPort: int | None = None
    workerJanPort: int | None = None
    discoveryPort: int | None = None
    discoveryInterval: int | None = None
    webAgentEnabled: bool | None = None
    supabaseEnabled: bool | None = None
    agentReputationEnabled: bool | None = None


class DirectChatRequest(BaseModel):
    """Request para chat directo a modelo"""

    message: str
    model: str
    engine: str = "groq"
    temperature: float = 0.7
    max_tokens: int = 2048


class WakeWorkerRequest(BaseModel):
    """Request para despertar o conectar al Worker por RDP (manual)"""

    hostname: str | None = Field(
        default=None,
        description="Hostname del Worker (usa config si no se proporciona)",
    )
    username: str | None = Field(default=None, description="Usuario RDP (usa config si no se proporciona)")
    password: str | None = Field(default=None, description="Contraseña RDP (usa config si no se proporciona)")


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
            from backend.adapters.web_agent import SITE_CONFIGS, WebAgentClient

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
    hybrid_memory = get_hybrid_memory_v2()
    persistent_queue_size = await hybrid_memory.get_persistent_queue_size()

    # Métricas de debates (deberían venir de los controllers)
    # Por ahora retornamos valores simulados
    return {
        "activeDebates": 0,
        "totalTokens": 0,
        "avgLatency": 0,
        "cpuUsage": cpu_percent,
        "memoryUsage": memory.percent,
        "supabaseSyncQueueSize": persistent_queue_size,
    }


@router.get("/analytics", dependencies=[Depends(require_admin_access)])
async def get_analytics_endpoint(limit: int = 5):
    """Resumen operativo básico del Data Warehouse."""
    safe_limit = max(1, min(limit, 25))

    async with AsyncSessionLocal() as db:
        daily_result = await db.execute(select(DailyMetricsSnapshot).order_by(desc(DailyMetricsSnapshot.date)).limit(1))
        daily = daily_result.scalar_one_or_none()

        topics_result = await db.execute(
            select(TopicTrending).order_by(desc(TopicTrending.debate_count), desc(TopicTrending.date)).limit(safe_limit)
        )
        topics = topics_result.scalars().all()

        models_result = await db.execute(
            select(ModelPerformance)
            .order_by(
                desc(ModelPerformance.success_rate),
                desc(ModelPerformance.total_turns),
                desc(ModelPerformance.avg_tokens_out),
            )
            .limit(safe_limit)
        )
        models = models_result.scalars().all()

    return {
        "dailySummary": None
        if not daily
        else {
            "date": daily.date,
            "totalDebatesCompleted": daily.total_debates_completed,
            "totalDebatesFailed": daily.total_debates_failed,
            "totalTurnsExecuted": daily.total_turns_executed,
            "totalTokensGenerated": daily.total_tokens_generated,
            "totalCostUsd": daily.total_cost_usd,
            "avgDebateDurationSeconds": daily.avg_debate_duration_seconds,
            "uniqueTopicsCount": daily.unique_topics_count,
            "activeModelsCount": daily.active_models_count,
        },
        "topTopics": [
            {
                "date": topic.date,
                "topic": topic.topic_text,
                "topicHash": topic.topic_hash,
                "debateCount": topic.debate_count,
                "totalTurns": topic.total_turns,
                "avgDurationSeconds": topic.avg_duration_seconds,
                "uniqueModelsCount": topic.unique_models_count,
            }
            for topic in topics
        ],
        "modelLeaderboard": [
            {
                "model": model.model_name,
                "provider": model.provider,
                "engine": model.engine,
                "agentRole": model.agent_role,
                "totalTurns": model.total_turns,
                "avgTokensOut": model.avg_tokens_out,
                "avgLatencyMs": model.avg_latency_ms,
                "successRate": model.success_rate,
            }
            for model in models
        ],
    }


@router.get("/health/sync", dependencies=[Depends(require_admin_access)])
async def get_sync_health_endpoint():
    """Estado accionable de sincronización Supabase y cola persistente."""
    hybrid_memory = get_hybrid_memory_v2()
    supabase_enabled = bool(getattr(hybrid_memory.supabase, "enabled", False))
    configured = bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)
    now = datetime.now()

    async with AsyncSessionLocal() as db:
        pending_count = (
            await db.scalar(
                select(func.count(SupabaseSyncQueueItem.id)).where(SupabaseSyncQueueItem.status == "pending")
            )
            or 0
        )
        retry_count = (
            await db.scalar(
                select(func.count(SupabaseSyncQueueItem.id))
                .where(SupabaseSyncQueueItem.status == "pending")
                .where(SupabaseSyncQueueItem.retry_count > 0)
            )
            or 0
        )
        due_count = (
            await db.scalar(
                select(func.count(SupabaseSyncQueueItem.id))
                .where(SupabaseSyncQueueItem.status == "pending")
                .where(SupabaseSyncQueueItem.next_attempt_at <= now)
            )
            or 0
        )
        last_error_item = (
            await db.execute(
                select(SupabaseSyncQueueItem)
                .where(SupabaseSyncQueueItem.last_error.is_not(None))
                .order_by(desc(SupabaseSyncQueueItem.updated_at))
                .limit(1)
            )
        ).scalar_one_or_none()

    if not supabase_enabled:
        status = "disabled"
        recommendation = "Configura SUPABASE_URL y SUPABASE_ANON_KEY para activar sincronizacion cloud."
    elif pending_count == 0:
        status = "healthy"
        recommendation = "La cola esta vacia y la sincronizacion no requiere accion."
    elif retry_count > 0 and due_count > 0:
        status = "blocked"
        recommendation = "Hay items vencidos con reintentos; revisa credenciales, permisos o conectividad Supabase."
    else:
        status = "degraded"
        recommendation = "Hay items pendientes; espera el backoff o revisa si la cola crece sostenidamente."

    return {
        "status": status,
        "supabase": {
            "enabled": supabase_enabled,
            "configured": configured,
            "urlConfigured": bool(settings.SUPABASE_URL),
            "anonKeyConfigured": bool(settings.SUPABASE_ANON_KEY),
        },
        "queue": {
            "pending": pending_count,
            "withRetries": retry_count,
            "dueNow": due_count,
            "inMemory": hybrid_memory.get_stats()["queue_size"],
            "lastError": None
            if not last_error_item
            else {
                "debateId": last_error_item.debate_id,
                "retryCount": last_error_item.retry_count,
                "message": last_error_item.last_error,
                "nextAttemptAt": last_error_item.next_attempt_at.isoformat(),
            },
        },
        "recommendation": recommendation,
    }


@router.get("/tribunal/config", dependencies=[Depends(require_admin_access)])
async def get_tribunal_config_endpoint():
    """Configuración efectiva del Tribunal y sus fallbacks."""
    role_configs = build_tribunal_config(settings)

    def serialize_agent(config):
        return {
            "slot": config.slot,
            "node": config.node,
            "engine": config.engine,
            "model": config.model,
            "roleLabel": config.role_label,
            "temperature": config.temperature,
            "maxTokens": config.max_tokens,
        }

    return {
        "maxIterations": settings.TRIBUNAL_MAX_ITERATIONS,
        "cloudFallbackEnabled": settings.TRIBUNAL_ENABLE_CLOUD_FALLBACK,
        "roles": {
            role: {
                "primary": serialize_agent(role_config.primary),
                "fallbacks": [serialize_agent(config) for config in role_config.fallbacks],
            }
            for role, role_config in role_configs.items()
        },
    }


@router.get("/reductio/analytics", dependencies=[Depends(require_admin_access)])
async def get_reductio_analytics_endpoint(limit: int = 10):
    """Analiticas de pruebas Reductio ad Absurdum."""
    safe_limit = max(1, min(limit, 50))

    async with AsyncSessionLocal() as db:
        total_proofs = await db.scalar(select(func.count(ReductioAbsurdumProof.id))) or 0

        avg_confidence = await db.scalar(select(func.avg(ReductioAbsurdumProof.confidence_score)))
        avg_confidence = round(float(avg_confidence), 3) if avg_confidence else 0.0

        avg_complacency_risk = await db.scalar(select(func.avg(ReductioAbsurdumProof.overall_complacency_risk)))
        avg_complacency_risk = round(float(avg_complacency_risk), 3) if avg_complacency_risk else 0.0

        invalid_count = (
            await db.scalar(select(func.count(ReductioAbsurdumProof.id)).where(not ReductioAbsurdumProof.is_valid)) or 0
        )

        recent_proofs_result = await db.execute(
            select(ReductioAbsurdumProof).order_by(desc(ReductioAbsurdumProof.created_at)).limit(safe_limit)
        )
        recent_proofs = recent_proofs_result.scalars().all()

        top_challenged_result = await db.execute(
            select(
                ReductioAbsurdumProof.challenged_agent,
                func.count(ReductioAbsurdumProof.id).label("challenge_count"),
                func.avg(ReductioAbsurdumProof.confidence_score).label("avg_confidence"),
            )
            .group_by(ReductioAbsurdumProof.challenged_agent)
            .order_by(desc("challenge_count"))
            .limit(safe_limit)
        )
        top_challenged = top_challenged_result.all()

        top_questioners_result = await db.execute(
            select(
                ReductioAbsurdumProof.questioning_agent,
                func.count(ReductioAbsurdumProof.id).label("proof_count"),
                func.avg(ReductioAbsurdumProof.confidence_score).label("avg_confidence"),
            )
            .group_by(ReductioAbsurdumProof.questioning_agent)
            .order_by(desc("proof_count"))
            .limit(safe_limit)
        )
        top_questioners = top_questioners_result.all()

        high_risk_proofs = (
            await db.scalar(
                select(func.count(ReductioAbsurdumProof.id)).where(
                    ReductioAbsurdumProof.overall_complacency_risk >= 0.7
                )
            )
            or 0
        )

        debates_with_proofs = await db.scalar(select(func.count(func.distinct(ReductioAbsurdumProof.debate_id)))) or 0

    recent_list = []
    for proof in recent_proofs:
        debate = await db.get(SequentialDebate, proof.debate_id)
        recent_list.append(
            {
                "id": proof.id,
                "debateId": proof.debate_id,
                "debateTopic": debate.topic if debate else "unknown",
                "iterationNumber": proof.iteration_number,
                "proposition": proof.proposition,
                "extremeCase": proof.extreme_case,
                "contradiction": proof.contradiction,
                "isValid": proof.is_valid,
                "confidenceScore": proof.confidence_score,
                "questioningAgent": proof.questioning_agent,
                "challengedAgent": proof.challenged_agent,
                "complacencyRisk": proof.overall_complacency_risk,
                "weakAssumptions": proof.weak_assumptions or [],
                "recommendations": proof.recommendations or [],
                "createdAt": proof.created_at.isoformat() if proof.created_at else None,
            }
        )

    return {
        "summary": {
            "totalProofs": total_proofs,
            "debatesWithProofs": debates_with_proofs,
            "avgConfidence": avg_confidence,
            "avgComplacencyRisk": avg_complacency_risk,
            "invalidProofs": invalid_count,
            "highRiskProofs": high_risk_proofs,
            "invalidationRate": round(invalid_count / total_proofs, 3) if total_proofs > 0 else 0.0,
        },
        "topChallengedAgents": [
            {
                "agent": row.challenged_agent,
                "challengeCount": row.challenge_count,
                "avgConfidence": round(float(row.avg_confidence), 3) if row.avg_confidence else 0.0,
            }
            for row in top_challenged
        ],
        "topQuestioners": [
            {
                "agent": row.questioning_agent,
                "proofCount": row.proof_count,
                "avgConfidence": round(float(row.avg_confidence), 3) if row.avg_confidence else 0.0,
            }
            for row in top_questioners
        ],
        "recentProofs": recent_list,
    }


@router.get("/health")
async def health_check_endpoint():
    """Health check del sistema con detección de Worker por servicios"""
    from backend.main import heartbeat_manager

    worker_connected = False
    worker_ip = None
    last_heartbeat = None

    # Método 1: Heartbeat TCP (si está activo)
    if heartbeat_manager:
        worker_connected = heartbeat_manager.is_alive()
        worker_ip = heartbeat_manager.get_peer_ip()
        last_heartbeat = heartbeat_manager.get_last_heartbeat_time()
        if last_heartbeat:
            last_heartbeat = last_heartbeat.isoformat()

    # Método 2: Si no hay heartbeat, verificar servicios del Worker
    if not worker_connected:
        try:
            from backend.engine.worker_launcher import worker_service_manager

            # Limpiar cache para obtener datos frescos
            worker_service_manager._check_cache = {}
            services = await worker_service_manager.check_all_services()
            running_count = sum(1 for s in services.values() if s.get("status") == "running")
            if running_count > 0:
                worker_connected = True
                resolved_ip = worker_service_manager._worker_ip or settings.get_worker_host()
                if resolved_ip:
                    worker_ip = resolved_ip
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Worker service check failed: {e}")

    # Fallback: si worker_connected pero sin IP, resolverla
    if worker_connected and not worker_ip:
        try:
            from backend.config import get_settings

            _settings = get_settings()
            worker_ip = _settings.get_worker_host()
        except Exception:
            pass

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "worker_connected": worker_connected,
        "worker_ip": worker_ip,
        "last_heartbeat": last_heartbeat,
        "transfer_speed": 0.0,
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
            rate_limit_id=client_ip,
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=result.message)

        return {
            "success": True,
            "message": result.message,
            "ip": result.ip,
            "duration_ms": result.duration_ms,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
        }

    except RDPSecurityError as e:
        raise HTTPException(status_code=400, detail=f"Error de seguridad: {e!s}")
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
            rate_limit_id="auto_wake",
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
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
        }

    except RDPRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {e!s}")


@router.get("/rdp-status", dependencies=[Depends(require_admin_access)])
async def rdp_status_endpoint():
    """Obtiene estado de configuración RDP (sin exponer credenciales)"""
    return {
        "enabled": settings.RDP_ENABLED,
        "hostname": settings.RDP_WORKER_HOSTNAME,
        "username": settings.RDP_WORKER_USERNAME.split("\\")[-1]
        if "\\" in settings.RDP_WORKER_USERNAME
        else settings.RDP_WORKER_USERNAME,
        "domain": settings.RDP_WORKER_USERNAME.split("\\")[0] if "\\" in settings.RDP_WORKER_USERNAME else None,
        "rate_limit_seconds": settings.RDP_RATE_LIMIT_SECONDS,
        "password_configured": bool(settings.RDP_WORKER_PASSWORD),
        "platform": "windows_only",
    }


# ─── Worker Services Management ──────────────────────────────────────


class WorkerServicesResponse(BaseModel):
    services: dict
    worker_ip: str | None = None


class WorkerLaunchRequest(BaseModel):
    service: str  # ollama, lm_studio, jan, all


@router.get("/worker/services", dependencies=[Depends(require_admin_access)])
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


@router.post("/worker/services/launch", dependencies=[Depends(require_admin_access)])
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


# ─── SQLite Backup Management ──────────────────────────────────────


class BackupResponse(BaseModel):
    success: bool
    filename: str | None = None
    bucket: str | None = None
    size_bytes: int | None = None
    timestamp: str | None = None
    url: str | None = None
    error: str | None = None
    reason: str | None = None


class BackupListItem(BaseModel):
    name: str
    size: int
    created_at: str | None = None
    updated_at: str | None = None


@router.post("/backup/create", dependencies=[Depends(require_admin_access)])
async def create_backup_endpoint():
    """Crea un backup de la base de datos SQLite y lo sube a Supabase Storage"""
    try:
        from backend.services.sqlite_backup import get_backup_service

        backup_service = get_backup_service()
        result = await backup_service.create_backup()

        if result.get("success"):
            return BackupResponse(
                success=True,
                filename=result.get("filename"),
                bucket=result.get("bucket"),
                size_bytes=result.get("size_bytes"),
                timestamp=result.get("timestamp"),
                url=result.get("url"),
            )
        else:
            return BackupResponse(
                success=False,
                error=result.get("error"),
                reason=result.get("reason"),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backup/list", dependencies=[Depends(require_admin_access)])
async def list_backups_endpoint(limit: int = 20):
    """Lista los backups disponibles en Supabase Storage"""
    try:
        from backend.services.sqlite_backup import get_backup_service

        backup_service = get_backup_service()
        backups = await backup_service.list_backups(limit=limit)

        return {
            "count": len(backups),
            "backups": [
                BackupListItem(
                    name=b["name"],
                    size=b["size"],
                    created_at=b.get("created_at"),
                    updated_at=b.get("updated_at"),
                )
                for b in backups
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backup/delete/{filename}", dependencies=[Depends(require_admin_access)])
async def delete_backup_endpoint(filename: str):
    """Elimina un backup especifico de Supabase Storage"""
    try:
        from backend.services.sqlite_backup import get_backup_service

        backup_service = get_backup_service()
        result = await backup_service.delete_backup(filename)

        if result.get("success"):
            return {"success": True, "message": f"Backup {filename} deleted"}
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Delete failed"))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/restore/{filename}", dependencies=[Depends(require_admin_access)])
async def restore_backup_endpoint(filename: str):
    """Descarga un backup de Supabase Storage para restauracion manual"""
    try:
        from backend.services.sqlite_backup import get_backup_service

        backup_service = get_backup_service()
        result = await backup_service.restore_backup(filename)

        if result.get("success"):
            return {
                "success": True,
                "filename": result.get("filename"),
                "size_bytes": result.get("size_bytes"),
                "download_path": result.get("download_path"),
                "message": result.get("message"),
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Restore failed"))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backup/status", dependencies=[Depends(require_admin_access)])
async def backup_status_endpoint():
    """Estado del servicio de backup"""
    try:
        from pathlib import Path as PathLib

        from backend.services.sqlite_backup import get_backup_service

        backup_service = get_backup_service()

        db_path = backup_service.db_path
        db_exists = PathLib(db_path).exists() if db_path else False
        db_size = PathLib(db_path).stat().st_size if db_exists else 0

        return {
            "enabled": backup_service.enabled,
            "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY),
            "database_path": db_path,
            "database_exists": db_exists,
            "database_size_bytes": db_size,
            "bucket": backup_service.BACKUP_BUCKET,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ApiKeyUpdateRequest(BaseModel):
    api_key: str


@router.post("/config/{service}/key", dependencies=[Depends(require_admin_access)])
async def update_api_key(service: str, req: ApiKeyUpdateRequest):
    """Actualiza una API key en tiempo de ejecucion."""
    valid_services = {
        "openrouter": "OPENROUTER_API_KEY",
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    if service not in valid_services:
        raise HTTPException(
            status_code=400, detail=f"Servicio no valido: {service}. Opciones: {list(valid_services.keys())}"
        )

    env_var = valid_services[service]
    setattr(settings, env_var, req.api_key)

    logger.info("system.api_key_updated", service=service, env_var=env_var)
    return {"success": True, "service": service, "message": f"API key para {service} actualizada"}


@router.post("/api-keys/{service}")
async def update_api_key_alias(service: str, req: ApiKeyUpdateRequest):
    """Alias para /config/{service}/key - compatibilidad con frontend."""
    return await update_api_key(service, req)


@router.get("/worker/resources")
async def get_worker_gpu_stats():
    """
    Consulta nvidia-smi en el Worker para obtener métricas GPU/RAM en tiempo real.
    Útil para diagnosticar OOM antes de que ocurran.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.free,memory.total,temperature.gpu,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 5:
                used, free, total, temp, util = parts
                return {
                    "gpu_memory_used_mb": int(used),
                    "gpu_memory_free_mb": int(free),
                    "gpu_memory_total_mb": int(total),
                    "gpu_temp_celsius": int(temp) if temp else None,
                    "gpu_utilization_pct": int(float(util)) if util else None,
                    "available": True,
                }
        return {"available": False, "error": f"nvidia-smi failed: {result.stderr.strip()[:200]}"}
    except FileNotFoundError:
        return {"available": False, "error": "nvidia-smi not found (no NVIDIA GPU or driver)"}
    except subprocess.TimeoutExpired:
        return {"available": False, "error": "nvidia-smi timed out"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@router.get("/worker/gpu/metrics")
async def get_gpu_metrics():
    """
    Obtiene metricas GPU actuales del colector.
    Incluye memoria, temperatura, utilizacion y procesos.
    """
    from backend.services.gpu_metrics import get_gpu_collector

    collector = get_gpu_collector()
    metrics = collector.collect()
    return {
        "available": metrics.is_available,
        "timestamp": metrics.timestamp.isoformat(),
        "gpu_name": metrics.gpu_name,
        "driver_version": metrics.driver_version,
        "memory": {
            "used_mb": metrics.memory_used_mb,
            "free_mb": metrics.memory_free_mb,
            "total_mb": metrics.memory_total_mb,
            "used_pct": metrics.memory_used_pct,
        },
        "temperature_celsius": metrics.temperature_celsius,
        "utilization_pct": metrics.utilization_pct,
        "power_watts": metrics.power_watts,
        "power_limit_watts": metrics.power_limit_watts,
        "fan_speed_pct": metrics.fan_speed_pct,
        "processes": metrics.processes,
        "error": metrics.error,
    }


@router.get("/worker/gpu/history")
async def get_gpu_history(limit: int = 50):
    """
    Obtiene historial de metricas GPU para graficos.
    """
    from backend.services.gpu_metrics import get_gpu_collector

    collector = get_gpu_collector()
    return {"history": collector.get_history(limit=limit)}


@router.get("/worker/gpu/summary")
async def get_gpu_summary():
    """
    Obtiene resumen estadistico de metricas GPU.
    """
    from backend.services.gpu_metrics import get_gpu_collector

    collector = get_gpu_collector()
    return collector.get_summary()


@router.get("/debates/{debate_id}/absurdum-analysis")
async def get_absurdum_analysis(debate_id: str):
    """
    Analisis de robustness por agente para un debate.
    Retorna proposiciones que fallaron, refinamientos aplicados, y scores.
    """
    try:
        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(AbsurdumProof).where(AbsurdumProof.debate_id == debate_id).order_by(AbsurdumProof.turn_number)
            )
            proofs = result.scalars().all()

            if not proofs:
                return {"debate_id": debate_id, "proofs": [], "summary": "No absurdum proofs found"}

            by_agent: dict[str, dict] = {}
            for p in proofs:
                key = f"{p.agent_model} ({p.agent_role})"
                if key not in by_agent:
                    by_agent[key] = {
                        "total_proofs": 0,
                        "contradictions_found": 0,
                        "avg_robustness": 0.0,
                        "refinements": 0,
                    }
                by_agent[key]["total_proofs"] += 1
                if p.contradiction_found:
                    by_agent[key]["contradictions_found"] += 1
                if p.refined_proposition:
                    by_agent[key]["refinements"] += 1
                if p.robustness_score is not None:
                    current_avg = by_agent[key]["avg_robustness"]
                    n = by_agent[key]["total_proofs"]
                    by_agent[key]["avg_robustness"] = current_avg + (p.robustness_score - current_avg) / n

            return {
                "debate_id": debate_id,
                "total_proofs": len(proofs),
                "by_agent": by_agent,
                "proofs": [
                    {
                        "turn_number": p.turn_number,
                        "agent_model": p.agent_model,
                        "agent_role": p.agent_role,
                        "original_proposition": p.original_proposition[:200],
                        "extreme_case_applied": p.extreme_case_applied[:200],
                        "contradiction_found": p.contradiction_found,
                        "refined_proposition": p.refined_proposition[:200] if p.refined_proposition else None,
                        "robustness_score": p.robustness_score,
                    }
                    for p in proofs
                ],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/circuit-breakers/status")
async def get_circuit_breakers_status():
    """
    Estado de todos los circuit breakers.
    """
    try:
        from backend.adapters.circuit_breaker import circuit_breakers

        status = circuit_breakers.get_all_status()
        return status
    except Exception as e:
        logger.error("circuit_breakers_status_error", error=str(e))
        return []


@router.post("/circuit-breakers/reset")
async def reset_circuit_breakers():
    """
    Resetea todos los circuit breakers.
    """
    try:
        from backend.adapters.circuit_breaker import circuit_breakers

        circuit_breakers.reset_all()
        return {"status": "ok", "message": "All circuit breakers reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-registry/models")
async def get_model_registry_models():
    """
    Obtiene todos los modelos registrados.
    Alias para compatibilidad con frontend.
    """
    try:
        from backend.engine.model_registry import model_registry

        return {
            "models": model_registry.get_available_models(),
        }
    except Exception as e:
        logger.error("model_registry_error", error=str(e))
        return {"models": []}


@router.post("/model-registry/refresh-rankings")
async def refresh_model_rankings():
    """
    Refresca los rankings de modelos.
    """
    try:
        from backend.engine.model_registry import model_registry

        model_registry.refresh_rankings()
        return {"status": "ok", "message": "Model rankings refreshed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
