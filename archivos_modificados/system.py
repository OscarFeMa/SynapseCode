"""
Synapse Council v3.0 - System API Routes
Endpoints para configuración, métricas y chat directo
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import psutil
import time

from backend.config import get_settings
from backend.engine.agent_orchestrator import AgentOrchestrator, AgentConfig

router = APIRouter(prefix="/system", tags=["System"])
settings = get_settings()
orchestrator = AgentOrchestrator()


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
    """Request para despertar o conectar al Worker por RDP"""
    hostname: str = "makederpc"
    username: str = "MAKEDER\\maked"
    password: str


@router.get("/settings")
async def get_settings_endpoint():
    """Obtiene configuración actual del sistema"""
    return {
        # API Keys (no retornar las keys completas por seguridad)
        openrouterKey: settings.OPENROUTER_API_KEY[:8] + "..." if settings.OPENROUTER_API_KEY else None,
        geminiKey: settings.GEMINI_API_KEY[:8] + "..." if settings.GEMINI_API_KEY else None,
        groqKey: settings.GROQ_API_KEY[:8] + "..." if settings.GROQ_API_KEY else None,
        deepseekKey: settings.DEEPSEEK_API_KEY[:8] + "..." if settings.DEEPSEEK_API_KEY else None,
        
        # Engine Configuration
        ollamaUrl: settings.OLLAMA_BASE_URL,
        lmStudioUrl: settings.LM_STUDIO_BASE_URL,
        janUrl: settings.JAN_BASE_URL,
        
        # Worker Configuration
        workerHost: settings.WORKER_HOST,
        workerOllamaPort: settings.WORKER_OLLAMA_PORT,
        workerLmStudioPort: settings.WORKER_LM_STUDIO_PORT,
        workerJanPort: settings.WORKER_JAN_PORT,
        
        # Discovery
        discoveryPort: settings.DISCOVERY_PORT,
        discoveryInterval: settings.DISCOVERY_INTERVAL,
        
        # Features
        webAgentEnabled: settings.WEB_AGENT_ENABLED,
        supabaseEnabled: settings.SUPABASE_ENABLED,
        agentReputationEnabled: settings.AGENT_REPUTATION_ENABLED
    }


@router.post("/settings")
async def update_settings_endpoint(req: SettingsRequest):
    """Actualiza configuración del sistema"""
    # Nota: En una implementación real, esto debería actualizar el archivo .env
    # Por ahora, solo retornamos éxito
    return {"success": True, "message": "Settings updated (implementación pendiente)"}


@router.post("/chat/direct")
async def direct_chat_endpoint(req: DirectChatRequest):
    """Chat directo a un modelo específico"""
    try:
        config = AgentConfig(
            slot="direct_chat",
            node="CLOUD",
            engine=req.engine,
            model=req.model,
            role_label="Direct Chat",
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )
        
        response_parts = []
        async for token in orchestrator.call_agent(
            config=config,
            user_prompt=req.message,
            system_prompt="Eres un asistente útil. Responde de manera concisa y directa."
        ):
            response_parts.append(token)
        
        return {
            "response": "".join(response_parts),
            "model": req.model,
            "engine": req.engine
        }
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


@router.post("/wake-worker")
async def wake_worker_endpoint(req: WakeWorkerRequest):
    """Abre el escritorio remoto hacia el Worker de forma automática e inyecta credenciales"""
    from backend.services.rdp_manager import RDPManager
    result = RDPManager.connect_to_worker(req.hostname, req.username, req.password)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result

