"""
Synapse Council v2.0 - Sequential Debate API Routes
Endpoints para debate secuencial multi-modelo
"""
import asyncio
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from pydantic import BaseModel
from datetime import datetime

from backend.engine.sequential_debate_controller import (
    SequentialDebateController,
    DebateAgent,
    AgentRole,
    get_standard_debate_config,
    get_local_only_config,
    get_cloud_ollama_config
)
from backend.engine.ultra_debate_controller import UltraDebateController
from backend.monitoring.prometheus import (
    record_debate_report_cache_hit,
    record_debate_report_generated,
)

router = APIRouter(prefix="/debates", tags=["Sequential Debate"])

# Controller singletons
debate_controller = SequentialDebateController()
ultra_controller = UltraDebateController()

class DebateRequest(BaseModel):
    """Request para crear un debate"""
    topic: str
    mode: str = "standard"  # standard, local_only, custom
    max_turns: Optional[int] = None
    include_cloud: bool = True
    agents: Optional[List[Dict[str, Any]]] = None  # Configuración personalizada de agentes


class DebateAgentResponse(BaseModel):
    """Respuesta de agente en el debate"""
    turn_number: int
    agent_name: str
    role: str
    model: str
    provider: str
    node: str
    response_preview: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class DebateResponse(BaseModel):
    """Respuesta completa del debate"""
    session_id: str
    topic: str
    status: str
    turns: List[DebateAgentResponse]
    final_verdict: Optional[str]
    total_tokens_in: int
    total_tokens_out: int
    total_latency_ms: int
    created_at: datetime
    completed_at: Optional[datetime]


class DebateStatusResponse(BaseModel):
    """Estado de una sesión de debate"""
    session_id: str
    status: str
    current_turn: Optional[int]
    total_turns: int
    topic: str


class DebateCreateResponse(BaseModel):
    session_id: str
    topic: str
    status: str
    mode: str
    total_turns: Optional[int] = None
    max_iterations: Optional[int] = None
    total_agents: Optional[int] = None
    features: Optional[List[str]] = None


class DebateContinueRequest(BaseModel):
    """Request para continuar un debate existente"""
    agents: Optional[List[Dict[str, Any]]] = None
    max_additional_turns: Optional[int] = None
    continuation_prompt: Optional[str] = None


class DebateTranscriptResponse(BaseModel):
    transcript: str
    source: str


class DebateReportResponse(BaseModel):
    session_id: str
    structured_report: Dict[str, Any]
    source: str


class DebateListResponse(BaseModel):
    count: int
    sessions: List[Dict[str, Any]]

@router.get("/list", response_model=DebateListResponse)
async def list_debates():
    """Lista todas las sesiones de debate activas (en memoria)"""
    sessions = debate_controller.list_sessions()
    return {
        "count": len(sessions),
        "sessions": [
            {
                "session_id": s.id,
                "topic": s.topic,
                "status": s.status,
                "turns_completed": len([t for t in s.turns if t.status == "completed"]),
                "total_turns": len(s.turns),
                "created_at": s.created_at
            }
            for s in sessions
        ]
    }

def build_debate_response(session) -> DebateResponse:
    """Helper para construir la respuesta estandarizada"""
    turns_response = []
    for turn in session.turns:
        # Manejar tanto DebateTurn (dataclass) como dict (desde BD)
        if hasattr(turn, "turn_number"):
            # Dataclass
            role_val = turn.agent.role.value if hasattr(turn.agent.role, "value") else turn.agent.role
            turns_response.append(DebateAgentResponse(
                turn_number=turn.turn_number,
                agent_name=turn.agent.name,
                role=str(role_val),
                model=turn.agent.model,
                provider=turn.agent.provider,
                node=turn.agent.node,
                response_preview=turn.response_received[:200] + "..." if len(turn.response_received) > 200 else turn.response_received,
                tokens_in=turn.tokens_in,
                tokens_out=turn.tokens_out,
                latency_ms=turn.latency_ms,
                status=turn.status,
                started_at=turn.started_at,
                completed_at=turn.completed_at
            ))
        else:
            # Dict
            turns_response.append(DebateAgentResponse(**turn))
            
    return DebateResponse(
        session_id=session.id,
        topic=session.topic,
        status=session.status,
        turns=turns_response,
        final_verdict=session.final_verdict,
        total_tokens_in=sum(t.tokens_in for t in session.turns),
        total_tokens_out=sum(t.tokens_out for t in session.turns),
        total_latency_ms=sum(t.latency_ms for t in session.turns),
        created_at=session.created_at,
        completed_at=session.completed_at
    )

# Import Supabase service
from backend.services.supabase_sync import get_supabase_service
supabase_service = get_supabase_service()


# ============================================================================
# Endpoints de Supabase (Nube) - DEBEN IR PRIMERO para evitar conflicto de rutas
# ============================================================================

@router.get("/cloud/status")
async def get_supabase_status():
    """Verifica estado de conexión con Supabase"""
    status = await supabase_service.test_connection()
    return {
        "enabled": supabase_service.enabled,
        "url": supabase_service.url,
        **status
    }


@router.get("/cloud/list")
async def list_cloud_debates(limit: int = 50):
    """Lista debates desde Supabase (nube)"""
    if not supabase_service.enabled:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    
    debates = await supabase_service.list_debates_from_cloud(limit)
    return {
        "source": "supabase_cloud",
        "count": len(debates),
        "debates": debates
    }


@router.get("/cloud/{session_id}")
async def get_cloud_debate(session_id: str):
    """Obtiene un debate específico desde Supabase"""
    if not supabase_service.enabled:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    
    debate = await supabase_service.get_debate_from_cloud(session_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found in Supabase")
    
    return {
        "source": "supabase_cloud",
        **debate
    }


@router.post("/cloud/sync/{session_id}")
async def sync_debate_to_cloud(session_id: str):
    """Fuerza sincronización manual de un debate a Supabase"""
    if not supabase_service.enabled:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    
    # Obtener desde BD local
    debate = await debate_controller.get_debate_from_db(session_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found in local database")
    
    # Preparar datos completos
    debate_data = {
        "id": debate["id"],
        "topic": debate["topic"],
        "mode": debate.get("mode", "standard"),
        "status": debate["status"],
        "total_turns": debate.get("total_turns", len(debate.get("turns", []))),
        "total_tokens_in": debate["total_tokens_in"],
        "total_tokens_out": debate["total_tokens_out"],
        "total_latency_ms": debate["total_latency_ms"],
        "final_verdict": debate.get("final_verdict"),
        "created_at": debate["created_at"],
        "completed_at": debate.get("completed_at"),
        "turns": debate.get("turns", [])
    }
    
    # Sincronizar
    result = await supabase_service.sync_debate(debate_data)
    
    if result.get("synced"):
        return {
            "message": "Debate synced to Supabase successfully",
            "session_id": session_id,
            "supabase_url": result.get("supabase_url"),
            "turns_synced": result.get("turns_synced")
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {result.get('error')}"
        )




@router.get("/history/list", response_model=DebateListResponse)
async def list_debate_history(limit: int = 50):
    """Lista debates históricos desde la base de datos"""
    
    debates = await debate_controller.list_debates_from_db(limit=limit)
    return {
        "count": len(debates),
        "sessions": debates
    }


@router.get("/reputation")
async def list_reputations(min_turns: int = 1) -> Dict[str, Any]:
    """
    Lista reputaciones de todos los modelos.
    Requiere: AGENT_REPUTATION_ENABLED=true en .env
    """
    try:
        from backend.engine.reputation_unified import reputation_service
        reps = await reputation_service.list_all(min_turns=min_turns)
        return {
            "status": "ok",
            "count": len(reps),
            "reputations": reps
        }
    except Exception as e:
        # logger.error("reputation.list_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error listing reputations: {str(e)}")


@router.get("/reputation/{model}/{role}")
async def get_reputation(model: str, role: str) -> Dict[str, Any]:
    """
    Obtiene reputación específica de un modelo para un rol.
    """
    try:
        from backend.engine.reputation_unified import reputation_service
        rep = await reputation_service.get_reputation(model, role)
        
        if rep is None:
            raise HTTPException(
                status_code=404,
                detail=f"No reputation found for {model}@{role}"
            )
        
        return {
            "status": "ok",
            "reputation": rep
        }
    except HTTPException:
        raise
    except Exception as e:
        # logger.error("reputation.get_error", model=model, role=role, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error getting reputation: {str(e)}")




@router.post("/create", status_code=202, response_model=DebateCreateResponse)
async def create_debate(request: DebateRequest, background_tasks: BackgroundTasks):
    """
    Crea y ejecuta un debate secuencial multi-modelo (Asincrono).
    Retorna session_id inmediatamente.
    """
    
    # 1. Crear ID y sesion base para que sea visible inmediatamente
    import uuid
    session_id = str(uuid.uuid4())
    
    # Seleccionar configuración
    if request.agents:
        # Usar configuración personalizada del usuario
        agents = []
        for agent_data in request.agents:
            agent = DebateAgent(
                id=agent_data.get("id", f"agent_{len(agents)}"),
                name=agent_data.get("name", "Agent"),
                role=AgentRole(agent_data.get("role", "analyst")),
                node=agent_data.get("node", "LOCAL"),
                engine=agent_data.get("engine", "ollama"),
                model=agent_data.get("model", "llama3.2:latest"),
                provider=agent_data.get("provider", "meta"),
                system_prompt=agent_data.get("system_prompt", ""),
                temperature=agent_data.get("temperature", 0.7),
                max_tokens=agent_data.get("max_tokens", 500)
            )
            agents.append(agent)
    elif request.mode == "local_only":
        agents = get_local_only_config(request.topic)
    elif request.mode == "cloud_ollama":
        agents = get_cloud_ollama_config(request.topic)
    elif request.mode == "ultra_crossing":
        # 1. Crear la sesión en el controlador de Ultra (esto la inicializa en memoria)
        # Nota: create_ultra_debate_with_id es async pero bloquea hasta el final
        
        async def run_ultra():
            # Ejecutar el debate (esto toma tiempo)
            await ultra_controller.create_ultra_debate_with_id(session_id, request.topic)
        
        # Registrar solo en ultra_controller (la API ya busca allí)
        background_tasks.add_task(run_ultra)
        return {"session_id": session_id, "topic": request.topic, "status": "accepted", "mode": "ultra_crossing"}
    else:
        agents = get_standard_debate_config(request.topic)
    
    # Limitar turns si se especifica
    if request.max_turns:
        agents = agents[:request.max_turns]
    
    # Filtrar cloud si no se quiere
    if not request.include_cloud:
        agents = [a for a in agents if a.node == "LOCAL"]
    
    # Tarea en segundo plano
    async def run_debate():
        await debate_controller.create_debate_with_id(
            session_id=session_id,
            topic=request.topic,
            agents_config=agents,
            on_turn_start=lambda turn: print(f"Turn {turn.turn_number}: {turn.agent.name} ({turn.agent.model})"),
            on_turn_complete=lambda turn: print(f"Completed: {turn.tokens_out} tokens in {turn.latency_ms}ms"),
            on_model_load=lambda model, provider: print(f"Loading: {model} ({provider})"),
            on_model_unload=lambda model, provider: print(f"Unloading: {model} ({provider})")
        )

    background_tasks.add_task(run_debate)
    
    return {
        "session_id": session_id, 
        "topic": request.topic, 
        "status": "accepted", 
        "mode": request.mode,
        "total_turns": len(agents)
    }


@router.post("/{session_id}/continue", status_code=202, response_model=DebateCreateResponse)
async def continue_debate(
    session_id: str,
    request: DebateContinueRequest,
    background_tasks: BackgroundTasks,
):
    """
    Continua un debate completado con nuevos turnos.
    Reutiliza el contexto acumulado y permite anadir instrucciones especificas.
    """
    session = debate_controller.get_session(session_id)
    if not session:
        debate_data = await debate_controller.get_debate_from_db(session_id)
        if not debate_data:
            raise HTTPException(status_code=404, detail="Debate not found")
        if debate_data.get("status") not in ("completed", "failed"):
            raise HTTPException(status_code=400, detail="Debate must be completed or failed to continue")
    
    if session and session.status not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Debate must be completed or failed to continue")
    
    agents = None
    if request.agents:
        agents = []
        for agent_data in request.agents:
            agent = DebateAgent(
                id=agent_data.get("id", f"agent_{len(agents)}"),
                name=agent_data.get("name", "Agent"),
                role=AgentRole(agent_data.get("role", "analyst")),
                node=agent_data.get("node", "LOCAL"),
                engine=agent_data.get("engine", "ollama"),
                model=agent_data.get("model", "llama3.2:latest"),
                provider=agent_data.get("provider", "meta"),
                system_prompt=agent_data.get("system_prompt", ""),
                temperature=agent_data.get("temperature", 0.7),
                max_tokens=agent_data.get("max_tokens", 500)
            )
            agents.append(agent)
    
    async def run_continuation():
        result = await debate_controller.continue_debate(
            session_id=session_id,
            agents_config=agents,
            max_additional_turns=request.max_additional_turns,
            continuation_prompt=request.continuation_prompt,
            on_turn_start=lambda turn: print(f"[Continue] Turn {turn.turn_number}: {turn.agent.name}"),
            on_turn_complete=lambda turn: print(f"[Continue] Completed: {turn.tokens_out} tokens in {turn.latency_ms}ms"),
        )
        if result:
            print(f"[Continue] Debate {session_id} continued with {len(result.turns)} total turns")

    background_tasks.add_task(run_continuation)
    
    existing_turns = len(session.turns) if session else 0
    return {
        "session_id": session_id,
        "topic": session.topic if session else "unknown",
        "status": "accepted",
        "mode": "continuation",
        "total_turns": existing_turns + (request.max_additional_turns or len(agents) if agents else 4),
        "features": ["continuation", "context_persistence"]
    }




@router.get("/{session_id}/report", response_model=DebateReportResponse)
async def get_debate_report(session_id: str):
    """Obtiene el informe estructurado JSON de un debate"""
    
    # Intentar desde memoria
    session = debate_controller.get_session(session_id)
    if session:
        if hasattr(session, 'structured_report') and session.structured_report:
            record_debate_report_cache_hit("memory")
            return {
                "session_id": session_id,
                "structured_report": session.structured_report,
                "source": "memory"
            }
        else:
            # Loguear que la sesión existe pero no tiene el reporte
            print(f"Session {session_id} found in memory but without structured report")
    
    # Intentar desde BD
    debate = await debate_controller.get_debate_from_db(session_id)
    if debate:
        if debate.get('structured_report'):
            record_debate_report_cache_hit("database")
            return {
                "session_id": session_id,
                "structured_report": debate['structured_report'],
                "source": "database"
            }
        if debate.get("status") == "completed":
            generated_report = await debate_controller.generate_structured_report_for_debate(session_id)
            if generated_report:
                record_debate_report_generated("database_backfill")
                return {
                    "session_id": session_id,
                    "structured_report": generated_report,
                    "source": "database_generated"
                }

        print(f"Debate {session_id} found in DB but without structured report")
    
    raise HTTPException(
        status_code=404, 
        detail=f"Structured report not found for session {session_id}. Session may still be running or report generation failed."
    )


@router.get("/{session_id}/status", response_model=DebateStatusResponse)
async def get_debate_status(session_id: str):
    """Obtiene el estado resumido de un debate"""
    
    session = debate_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Debate session not found")
    
    current_turn = None
    for turn in session.turns:
        if turn.status == "running":
            current_turn = turn.turn_number
            break
    
    return DebateStatusResponse(
        session_id=session.id,
        status=session.status,
        current_turn=current_turn,
        total_turns=len(session.turns),
        topic=session.topic
    )


@router.get("/{session_id}/transcript", response_model=DebateTranscriptResponse)
async def get_debate_transcript(session_id: str):
    """Obtiene la transcripción completa del debate (desde memoria o BD)"""
    
    # Primero intentar desde memoria (sesiones activas)
    session = debate_controller.get_session(session_id)
    if session:
        lines = [
            f"# TRANSCRIPCIÓN DEL DEBATE: {session.topic}",
            f"Session ID: {session.id}",
            f"Estado: {session.status}",
            f"Iniciado: {session.created_at}",
            ""
        ]
        
        for turn in session.turns:
            lines.extend([
                f"## Turno {turn.turn_number}: {turn.agent.name}",
                f"**Rol:** {turn.agent.role.value}",
                f"**Modelo:** {turn.agent.model} ({turn.agent.provider})",
                f"**Nodo:** {turn.agent.node}",
                f"**Tokens:** {turn.tokens_out} | **Tiempo:** {turn.latency_ms}ms",
                "",
                turn.response_received,
                "",
                "---",
                ""
            ])
        
        if session.final_verdict:
            lines.extend(["", session.final_verdict])
        
        return {"transcript": "\n".join(lines), "source": "memory"}
    
    # Si no está en memoria, buscar en BD
    debate_data = await debate_controller.get_debate_from_db(session_id)
    if debate_data:
        lines = [
            f"# TRANSCRIPCIÓN DEL DEBATE: {debate_data['topic']}",
            f"Session ID: {debate_data['id']}",
            f"Estado: {debate_data['status']}",
            f"Modo: {debate_data['mode']}",
            f"Creado: {debate_data['created_at']}",
            "",
            "## Estadísticas",
            f"- Tokens In: {debate_data['total_tokens_in']:,}",
            f"- Tokens Out: {debate_data['total_tokens_out']:,}",
            ""
        ]
        
        for turn in debate_data['turns']:
            lines.extend([
                f"## Turno {turn['turn_number']}: {turn['agent_name']}",
                f"**Rol:** {turn['agent_role']}",
                f"**Modelo:** {turn['model']} ({turn['provider']})",
                f"**Nodo:** {turn['node']}",
                f"**Tokens:** {turn['tokens_out']} | **Tiempo:** {turn['latency_ms']}ms",
                f"**Estado:** {turn['status']}",
                "",
                turn['response_preview'],
                "",
                "---",
                ""
            ])
        
        if debate_data.get('final_verdict'):
            lines.extend(["", debate_data['final_verdict']])
        
        # Agregar info de archivo si existe
        if debate_data.get('transcript_path'):
            lines.extend([
                "",
                f"📄 **Archivo completo:** `{debate_data['transcript_path']}`"
            ])
        
        return {"transcript": "\n".join(lines), "source": "database"}
    
    raise HTTPException(status_code=404, detail="Debate session not found in memory or database")




@router.get("/history/{session_id}")
async def get_historical_debate(session_id: str):
    """Obtiene un debate histórico desde la base de datos"""
    
    debate = await debate_controller.get_debate_from_db(session_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found in database")
    
    return debate


@router.get("/history/{session_id}/file")
async def get_debate_file(session_id: str):
    """Obtiene la ruta del archivo de transcripción guardado"""
    
    debate = await debate_controller.get_debate_from_db(session_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    if not debate.get('transcript_path'):
        raise HTTPException(status_code=404, detail="Transcript file not found for this debate")
    
    # Leer archivo
    import os
    filepath = debate['transcript_path']
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "session_id": session_id,
            "filepath": filepath,
            "content": content,
            "size_bytes": len(content)
        }
    else:
        raise HTTPException(status_code=404, detail=f"File not found: {filepath}")


@router.delete("/{session_id}")
async def delete_debate(session_id: str):
    """Elimina una sesión de debate"""
    
    session = debate_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Debate session not found")
    
    del debate_controller.active_sessions[session_id]
    return {"message": "Debate session deleted from memory", "session_id": session_id}


# ============================================================================
# CONSENSUS DEBATE ENDPOINTS
# ============================================================================

from backend.engine.consensus_debate_controller import (
    ConsensusDebateController,
    get_consensus_debate_config
)

consensus_controller = ConsensusDebateController()


class ConsensusRequest(BaseModel):
    """Request para crear debate de consenso"""
    topic: str
    max_rounds: Optional[int] = 5


@router.post("/consensus/create", status_code=202, response_model=DebateCreateResponse)
async def create_consensus_debate(request: ConsensusRequest, background_tasks: BackgroundTasks):
    """
    Crea debate de CONSENSO (Asincrono).
    """
    import uuid
    session_id = str(uuid.uuid4())
    
    agents = get_consensus_debate_config(request.topic)
    
    if request.max_rounds:
        consensus_controller.MAX_ROUNDS = request.max_rounds
    
    async def run_consensus():
        await consensus_controller.create_consensus_debate_with_id(
            session_id=session_id,
            topic=request.topic,
            agents_config=agents,
            on_round_complete=lambda r: print(f"Round {r.round_number}: {r.global_consensus_score:.1%}"),
            on_consensus_update=lambda s, st: print(f"Consensus: {s:.1%} [{st}]")
        )

    background_tasks.add_task(run_consensus)
    
    return {
        "session_id": session_id,
        "topic": request.topic,
        "status": "accepted",
        "total_agents": len(agents)
    }


# ============================================================================
# DEBATE ITERATIVO CON CRUZAMIENTOS
# ============================================================================

class IterativeDebateRequest(BaseModel):
    """Request para crear debate iterativo avanzado"""
    topic: str
    mode: str = "iterative"
    max_iterations: Optional[int] = 3
    agents: Optional[List[Dict[str, Any]]] = None


@router.post("/create/iterative", status_code=202, response_model=DebateCreateResponse)
async def create_iterative_debate(request: IterativeDebateRequest, background_tasks: BackgroundTasks):
    """
    Crea debate ITERATIVO avanzado con múltiples fases:
    - Análisis inicial de cada agente
    - Cruzamientos críticos (agentes se responden entre sí)
    - Validación de argumentos
    - Búsqueda de consenso
    
    El contexto se mantiene entre iteraciones para refinamiento progresivo.
    """
    import uuid
    session_id = str(uuid.uuid4())
    
    # Seleccionar configuración
    if request.agents:
        # Usar configuración personalizada del usuario
        agents = []
        for agent_data in request.agents:
            agent = DebateAgent(
                id=agent_data.get("id", f"agent_{len(agents)}"),
                name=agent_data.get("name", "Agent"),
                role=AgentRole(agent_data.get("role", "analyst")),
                node=agent_data.get("node", "LOCAL"),
                engine=agent_data.get("engine", "ollama"),
                model=agent_data.get("model", "mistral:7b"),
                provider=agent_data.get("provider", "mistral"),
                system_prompt=agent_data.get("system_prompt", ""),
                temperature=agent_data.get("temperature", 0.7),
                max_tokens=agent_data.get("max_tokens", 800)
            )
            agents.append(agent)
    else:
        # Usar configuración iterativa por defecto
        agents = [
            DebateAgent(
                id="analyst_1",
                name="Analista Principal",
                role=AgentRole.ANALYST,
                node="LOCAL",
                engine="ollama",
                model="mistral:7b",
                provider="mistral",
                system_prompt="Analiza el tema desde una perspectiva integral y fundamentada.",
                temperature=0.7,
                max_tokens=800
            ),
            DebateAgent(
                id="critic_1",
                name="Crítico Especializado",
                role=AgentRole.CRITIC,
                node="LOCAL",
                engine="ollama",
                model="llama3:8b",
                provider="meta",
                system_prompt="Cuestiona los argumentos presentados con rigor constructivo.",
                temperature=0.6,
                max_tokens=700
            ),
            DebateAgent(
                id="validator_1",
                name="Validador",
                role=AgentRole.VALIDATOR,
                node="LOCAL",
                engine="ollama",
                model="deepseek-r1:7b",
                provider="deepseek",
                system_prompt="Valida la solidez lógica y factual de los argumentos.",
                temperature=0.4,
                max_tokens=600
            )
        ]
    
    max_iterations = request.max_iterations or 3
    
    async def run_iterative():
        await debate_controller.run_iterative_debate(
            session_id=session_id,
            topic=request.topic,
            agents_config=agents,
            max_iterations=max_iterations,
            on_iteration_complete=lambda i: print(f"Iteración {i.iteration_number} completada: {len(i.turns)} turnos, {len(i.cruzamientos)} cruzamientos"),
            on_cruzamiento=lambda c: print(f"Cruzamiento: {c.from_agent} → {c.to_agent}")
        )
    
    background_tasks.add_task(run_iterative)
    
    return {
        "session_id": session_id,
        "topic": request.topic,
        "status": "accepted",
        "mode": "iterative",
        "max_iterations": max_iterations,
        "total_agents": len(agents),
        "features": [
            "multi_iteration",
            "context_persistence",
            "critical_crossings",
            "validation_phase",
            "consensus_search"
        ]
    }


# ============================================================================
# ENDPOINTS DE REPUTACIÓN EMA
# ============================================================================

@router.get("/{session_id}", response_model=DebateResponse)
async def get_debate(session_id: str):
    """Obtiene el estado completo de una sesión de debate"""
    
    # Primero buscar en debate_controller (standard, local_only, cloud_ollama)
    session = debate_controller.get_session(session_id)
    if session:
        return build_debate_response(session)
    
    # Si no está, buscar en ultra_controller (ultra_crossing)
    session = ultra_controller.active_sessions.get(session_id)
    if session:
        return build_debate_response(session)
    
    raise HTTPException(status_code=404, detail="Debate session not found")


# ============================================================================
# EXPORTACIÓN DE RESULTADOS
# ============================================================================

def _build_clean_turns(session) -> list:
    """Construye lista limpia de intervenciones: rol, quien, que dijo"""
    turns = []
    for t in session.turns:
        if t.status.startswith("completed"):
            turns.append({
                "turno": t.turn_number,
                "rol": t.agent.role.value,
                "agente": t.agent.name,
                "modelo": f"{t.agent.model} ({t.agent.provider})",
                "intervencion": t.response_received.strip(),
                "tokens": t.tokens_out,
                "tiempo_ms": t.latency_ms,
            })
    return turns


def _serialize_turn(turn) -> Dict[str, Any]:
    """Serializa un turno a formato estructurado uniforme."""
    if hasattr(turn, "turn_number"):
        role_value = turn.agent.role.value if hasattr(turn.agent.role, "value") else str(turn.agent.role)
        return {
            "turn_number": turn.turn_number,
            "agent": {
                "id": turn.agent.id,
                "name": turn.agent.name,
                "role": role_value,
                "model": turn.agent.model,
                "provider": turn.agent.provider,
                "node": turn.agent.node,
                "engine": turn.agent.engine,
            },
            "content": turn.response_received.strip(),
            "metrics": {
                "tokens_in": turn.tokens_in,
                "tokens_out": turn.tokens_out,
                "latency_ms": turn.latency_ms,
            },
            "status": turn.status,
            "started_at": turn.started_at.isoformat() if turn.started_at else None,
            "completed_at": turn.completed_at.isoformat() if turn.completed_at else None,
        }

    return {
        "turn_number": turn.get("turn_number"),
        "agent": {
            "id": turn.get("agent_id"),
            "name": turn.get("agent_name"),
            "role": turn.get("agent_role"),
            "model": turn.get("model"),
            "provider": turn.get("provider"),
            "node": turn.get("node"),
            "engine": turn.get("engine"),
        },
        "content": (turn.get("response_received") or turn.get("response_preview") or "").strip(),
        "metrics": {
            "tokens_in": turn.get("tokens_in", 0),
            "tokens_out": turn.get("tokens_out", 0),
            "latency_ms": turn.get("latency_ms", 0),
        },
        "status": turn.get("status"),
        "started_at": turn.get("started_at").isoformat() if hasattr(turn.get("started_at"), "isoformat") else turn.get("started_at"),
        "completed_at": turn.get("completed_at").isoformat() if hasattr(turn.get("completed_at"), "isoformat") else turn.get("completed_at"),
    }


def _serialize_iterations(session) -> List[Dict[str, Any]]:
    """Serializa iteraciones si existen en memoria."""
    iterations = []
    for iteration in getattr(session, "iterations", []) or []:
        iterations.append({
            "number": iteration.iteration_number,
            "phase": iteration.phase,
            "started_at": iteration.started_at.isoformat() if iteration.started_at else None,
            "completed_at": iteration.completed_at.isoformat() if iteration.completed_at else None,
            "consensus_points": iteration.consensus_points,
            "dissent_areas": iteration.disagreement_points,
            "turns": [_serialize_turn(turn) for turn in iteration.turns if turn.status.startswith("completed")],
            "cross_references": [
                {
                    "from_agent": cruzamiento.from_agent,
                    "to_agent": cruzamiento.to_agent,
                    "target_argument": cruzamiento.target_argument,
                    "response": cruzamiento.response,
                    "iteration": cruzamiento.iteration,
                    "timestamp": cruzamiento.timestamp.isoformat() if cruzamiento.timestamp else None,
                }
                for cruzamiento in iteration.cruzamientos
            ],
        })
    return iterations


def _build_structured_export_from_session(session) -> Dict[str, Any]:
    """Construye exportación estructurada enriquecida desde sesión en memoria."""
    serialized_turns = [
        _serialize_turn(turn)
        for turn in session.turns
        if turn.status.startswith("completed")
    ]
    total_tokens_out = sum(turn["metrics"]["tokens_out"] for turn in serialized_turns)
    total_latency_ms = sum(turn["metrics"]["latency_ms"] for turn in serialized_turns)

    export = {
        "debate_id": session.id,
        "topic": session.topic,
        "status": session.status,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "duration_seconds": round((session.completed_at - session.created_at).total_seconds(), 1) if session.completed_at and session.created_at else None,
        "final_verdict": session.final_verdict,
        "structured_report": session.structured_report,
        "summary": {
            "total_turns": len(session.turns),
            "completed_turns": len(serialized_turns),
            "total_tokens_out": total_tokens_out,
            "total_latency_ms": total_latency_ms,
        },
        "interventions": serialized_turns,
        "intervenciones": _build_clean_turns(session),
        "iterations": _serialize_iterations(session),
    }

    if hasattr(session, "tribunal_verdict") and session.tribunal_verdict:
        export["tribunal_verdict"] = session.tribunal_verdict

    return export


def _build_structured_export_from_db(session_id: str, debate_data: Dict[str, Any]) -> Dict[str, Any]:
    """Construye exportación estructurada enriquecida desde datos persistidos."""
    serialized_turns = [
        _serialize_turn(turn)
        for turn in debate_data.get("turns", [])
        if str(turn.get("status", "")).startswith("completed")
    ]

    return {
        "debate_id": session_id,
        "topic": debate_data.get("topic"),
        "mode": debate_data.get("mode"),
        "status": debate_data.get("status"),
        "created_at": debate_data.get("created_at").isoformat() if hasattr(debate_data.get("created_at"), "isoformat") else debate_data.get("created_at"),
        "completed_at": debate_data.get("completed_at").isoformat() if hasattr(debate_data.get("completed_at"), "isoformat") else debate_data.get("completed_at"),
        "final_verdict": debate_data.get("final_verdict"),
        "structured_report": debate_data.get("structured_report"),
        "transcript_path": debate_data.get("transcript_path"),
        "summary": {
            "total_turns": len(debate_data.get("turns", [])),
            "completed_turns": len(serialized_turns),
            "total_tokens_out": debate_data.get("total_tokens_out", 0),
            "total_latency_ms": debate_data.get("total_latency_ms", 0),
        },
        "interventions": serialized_turns,
        "iterations": [],
    }


@router.get("/{session_id}/export/json")
async def export_debate_json(session_id: str):
    """Exporta el debate en JSON estructurado con metadata e intervenciones."""
    session = debate_controller.get_session(session_id)
    if not session:
        session_data = await debate_controller.get_debate_from_db(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Debate not found")
        content = json.dumps(
            _build_structured_export_from_db(session_id, session_data),
            indent=2,
            ensure_ascii=False,
        )
    else:
        content = json.dumps(
            _build_structured_export_from_session(session),
            indent=2,
            ensure_ascii=False,
        )
    
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=debate_{session_id}.json"}
    )


@router.get("/{session_id}/export/markdown")
async def export_debate_markdown(session_id: str):
    """Exporta el debate como Markdown limpio"""
    session = debate_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Debate not found")

    lines = [
        f"# {session.topic}",
        f"",
        f"_{'finalizado' if session.status == 'completed' else 'en progreso'}_ | "
        f"{len(session.turns)} intervenciones",
        f"",
    ]
    
    for turn in session.turns:
        if turn.status.startswith("completed"):
            role_tag = {
                "analyst": "📊 Analista",
                "critic": "⚡ Crítico",
                "synthesizer": "🔗 Sintetizador",
                "refiner": "🔧 Refinador",
                "moderator": "⚖️ Moderador",
                "validator": "✅ Validador",
                "consensus": "🤝 Consenso",
            }.get(turn.agent.role.value, "💬")
            
            lines.extend([
                f"## {role_tag} — {turn.agent.name}",
                f"",
                f"_{turn.agent.model}_",
                f"",
                turn.response_received.strip(),
                f"",
                f"---",
                f"",
            ])
    
    if session.final_verdict:
        lines.extend([
            f"## ⚖️ Veredicto Final",
            f"",
            session.final_verdict.strip(),
        ])
    
    content = "\n".join(lines)
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=debate_{session_id}.md"}
    )


@router.get("/{session_id}/export/pdf")
async def export_debate_pdf(session_id: str):
    """Exporta el debate como HTML imprimible (listo para PDF desde navegador)"""
    session = debate_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    turns_html = ""
    for turn in session.turns:
        if turn.status.startswith("completed"):
            role_icon = {"analyst":"📊","critic":"⚡","synthesizer":"🔗","refiner":"🔧","moderator":"⚖️","validator":"✅","consensus":"🤝"}
            icon = role_icon.get(turn.agent.role.value, "💬")
            text = turn.response_received.strip().replace("\n", "<br>")
            turns_html += f"""
            <div class="turn">
                <div class="turn-header">{icon} <strong>{turn.agent.name}</strong> <span class="role">({turn.agent.role.value})</span></div>
                <div class="turn-model">{turn.agent.model}</div>
                <div class="turn-text">{text}</div>
            </div>"""
    
    verdict_html = ""
    if session.final_verdict:
        verdict_html = f"""
        <div class="verdict">
            <h2>⚖️ Veredicto Final</h2>
            <p>{session.final_verdict.strip().replace(chr(10), '<br>')}</p>
        </div>"""
    
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Debate: {session.topic[:60]}</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #1e293b; line-height: 1.6; }}
  h1 {{ color: #2563eb; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }}
  h2 {{ color: #1e293b; margin-top: 24px; }}
  .meta {{ color: #64748b; font-size: 0.85rem; margin-bottom: 24px; }}
  .turn {{ background: #f8fafc; border-left: 4px solid #2563eb; padding: 12px 16px; margin: 12px 0; border-radius: 0 6px 6px 0; }}
  .turn-header {{ font-size: 1.05rem; margin-bottom: 2px; }}
  .role {{ color: #64748b; font-size: 0.8rem; font-weight: normal; }}
  .turn-model {{ color: #94a3b8; font-size: 0.75rem; margin-bottom: 8px; }}
  .turn-text {{ white-space: pre-wrap; font-size: 0.9rem; }}
  .verdict {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px; margin: 20px 0; border-radius: 0 6px 6px 0; }}
  hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 16px 0; }}
  @media print {{ body {{ margin: 20px; }} .turn {{ break-inside: avoid; }} }}
</style>
</head><body>
<h1>{session.topic}</h1>
<div class="meta">
  {len(session.turns)} intervenciones | {session.status} |
  {session.created_at.strftime('%d/%m/%Y %H:%M') if session.created_at else ''}
</div>
{turns_html}
{verdict_html}
</body></html>"""
    
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f"inline; filename=debate_{session_id}.html"}
    )
