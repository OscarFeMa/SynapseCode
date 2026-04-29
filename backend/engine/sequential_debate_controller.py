"""
Synapse Council v2.0 - Sequential Multi-Model Debate Controller
Debate secuencial con carga/descarga dinámica de modelos
"""
import asyncio
import uuid
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
import json

from backend.engine.local_engine_manager import LocalEngineManager, EngineType
from backend.adapters.openrouter import OpenRouterClient
from backend.config import get_settings
from backend.database.local_db import AsyncSessionLocal
from backend.database.models import SequentialDebate, SequentialDebateTurn
from backend.services.supabase_sync import get_supabase_service
from backend.engine.tribunal import TribunalCouncil
from backend.engine.convergence import ConvergenceEvaluator
from backend.engine.quality_monitor import is_response_usable, evaluate_response

settings = get_settings()
logger = structlog.get_logger()
supabase_service = get_supabase_service()

# Directorio para transcripts
TRANSCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'debates')
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


class AgentRole(Enum):
    """Roles disponibles para agentes en el debate"""
    ANALYST = "analyst"           # Analiza el tema propuesto
    CRITIC = "critic"             # Critica el análisis anterior
    SYNTHESIZER = "synthesizer"   # Síntesis de argumentos
    REFINER = "refiner"           # Refina conclusiones
    MODERATOR = "moderator"       # Moderador/veredicto final


@dataclass
class DebateAgent:
    """Configuración de un agente en el debate secuencial"""
    id: str
    name: str
    role: AgentRole
    node: str  # LOCAL, CLOUD
    engine: str  # ollama, openrouter
    model: str
    provider: str  # meta, mistral, qwen, openrouter, etc.
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 1000
    

@dataclass
class DebateTurn:
    """Un turno del debate"""
    turn_number: int
    agent: DebateAgent
    prompt_sent: str
    response_received: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    quality_score: float = 1.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed


@dataclass
class DebateSession:
    """Sesión completa de debate"""
    id: str
    topic: str
    turns: List[DebateTurn] = field(default_factory=list)
    context_history: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "created"  # created, running, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    final_verdict: Optional[str] = None
    
    # Campos para Tribunal y Convergence (v2.1)
    tribunal_verdict: Optional[Dict[str, Any]] = None
    consensus_score: float = 0.0
    convergence_level: str = 'UNKNOWN'
    structured_report: Optional[Dict[str, Any]] = None
    
    def build_context_prompt(self, current_agent: DebateAgent) -> str:
        """Construye el prompt con todo el contexto acumulado"""
        lines = [
            f"# DEBATE SECUENCIAL: {self.topic}",
            "",
            "## Tu Rol",
            f"Eres: {current_agent.name}",
            f"Rol: {current_agent.role.value}",
            f"Modelo: {current_agent.model} ({current_agent.provider})",
            "",
            "## Historial del Debate"
        ]
        
        for turn in self.turns:
            if turn.status.startswith("completed"):
                # Filtro de calidad (v2.1)
                if not is_response_usable(turn.response_received, turn.agent.role.value):
                    logger.warning("sequential_debate.omitting_low_quality_turn", 
                                 turn=turn.turn_number, 
                                 agent=turn.agent.name)
                    continue

                lines.append(f"\n### Turno {turn.turn_number}: {turn.agent.name} ({turn.agent.role.value})")
                lines.append(f"**Modelo:** {turn.agent.model} ({turn.agent.provider})")
                lines.append(f"\n{turn.response_received}")
        
        lines.append("\n" + "="*60)
        lines.append("\n## Tu Tarea")
        
        return "\n".join(lines)


class SequentialDebateController:
    """
    Controller de debate secuencial multi-modelo:
    - Carga modelos uno por uno
    - Acumula contexto de cada turno
    - Descarga modelo tras uso
    - Alterna entre providers locales y cloud
    """
    
    def __init__(self):
        self.local_manager = LocalEngineManager()
        self.openrouter = OpenRouterClient() if settings.OPENROUTER_API_KEY else None
        self.active_sessions: Dict[str, DebateSession] = {}
        self.tribunal = TribunalCouncil()
        self.convergence_evaluator = ConvergenceEvaluator()
        
    async def create_debate(
        self,
        topic: str,
        agents_config: List[DebateAgent],
        on_turn_start: Optional[Callable[[DebateTurn], None]] = None,
        on_turn_complete: Optional[Callable[[DebateTurn], None]] = None,
        on_model_load: Optional[Callable[[str, str], None]] = None,
        on_model_unload: Optional[Callable[[str, str], None]] = None,
        mode: str = "standard"
    ) -> DebateSession:
        """Crea y ejecuta un debate secuencial con ID autogenerado"""
        session_id = str(uuid.uuid4())
        return await self.create_debate_with_id(
            session_id=session_id,
            topic=topic,
            agents_config=agents_config,
            on_turn_start=on_turn_start,
            on_turn_complete=on_turn_complete,
            on_model_load=on_model_load,
            on_model_unload=on_model_unload,
            mode=mode
        )

    async def create_debate_with_id(
        self,
        session_id: str,
        topic: str,
        agents_config: List[DebateAgent],
        on_turn_start: Optional[Callable[[DebateTurn], None]] = None,
        on_turn_complete: Optional[Callable[[DebateTurn], None]] = None,
        on_model_load: Optional[Callable[[str, str], None]] = None,
        on_model_unload: Optional[Callable[[str, str], None]] = None,
        mode: str = "standard"
    ) -> DebateSession:
        """Crea y ejecuta un debate secuencial con un ID proporcionado"""
        
        session = DebateSession(
            id=session_id,
            topic=topic,
            status="running"
        )
        self.active_sessions[session_id] = session
        
        # Crear registro en base de datos
        db_debate = None
        try:
            async with AsyncSessionLocal() as db_session:
                db_debate = SequentialDebate(
                    id=session_id,
                    topic=topic,
                    mode=mode,
                    status="running",
                    total_turns=len(agents_config)
                )
                db_session.add(db_debate)
                await db_session.commit()
                logger.info("sequential_debate.db_created", 
                           session_id=session_id)
        except Exception as e:
            logger.error("sequential_debate.db_error", 
                        session_id=session_id, 
                        error=str(e))
        
        logger.info("sequential_debate.created", 
                   session_id=session_id, 
                   topic=topic,
                   num_agents=len(agents_config))
        
        try:
            # Variable para rastrear el modelo anterior y liberarlo de RAM
            previous_model = None
            
            for idx, agent_config in enumerate(agents_config, 1):
                # Liberar modelo anterior de la RAM del worker antes de cargar el nuevo
                if previous_model and agent_config.node == "LOCAL" and agent_config.engine == "ollama":
                    try:
                        logger.info("sequential_debate.unloading_previous_model",
                                   session_id=session_id,
                                   previous_model=previous_model,
                                   current_agent=agent_config.name)
                        # Obtener el cliente Ollama del engine manager
                        ollama_client = self.engine_manager.engines.get(EngineType.OLLAMA)
                        if ollama_client:
                            await ollama_client.unload_model(previous_model)
                    except Exception as e:
                        logger.warning("sequential_debate.unload_failed",
                                      session_id=session_id,
                                      previous_model=previous_model,
                                      error=str(e))
                
                turn = DebateTurn(
                    turn_number=idx,
                    agent=agent_config,
                    prompt_sent="",
                    started_at=datetime.now()
                )
                turn.status = "running"
                
                # Callback: modelo cargándose
                if on_model_load:
                    on_model_load(agent_config.model, agent_config.provider)
                
                # Construir prompt con contexto acumulado
                context_prompt = session.build_context_prompt(agent_config)
                full_prompt = f"{context_prompt}\n\n{agent_config.system_prompt}"
                turn.prompt_sent = full_prompt
                
                if on_turn_start:
                    on_turn_start(turn)
                
                # Ejecutar turno
                logger.info("sequential_debate.turn_start",
                           session_id=session_id,
                           turn=idx,
                           agent=agent_config.name,
                           model=agent_config.model)
                
                try:
                    if agent_config.node == "LOCAL":
                        response = await self._run_local_agent(
                            agent_config, 
                            full_prompt,
                            on_model_unload
                        )
                    else:  # CLOUD
                        response = await self._run_cloud_agent(
                            agent_config,
                            full_prompt
                        )
                    
                    turn.response_received = response["text"]
                    turn.tokens_in = response["tokens_in"]
                    turn.tokens_out = response["tokens_out"]
                    turn.latency_ms = response["latency_ms"]
                    
                    # Evaluar calidad (v2.1)
                    q_score, _ = evaluate_response(turn.response_received, agent_config.role.value)
                    turn.quality_score = q_score
                    
                    turn.status = "completed"
                    turn.completed_at = datetime.now()
                    
                    # Actualizar el modelo anterior para liberarlo en el siguiente turno
                    if agent_config.node == "LOCAL" and agent_config.engine == "ollama":
                        previous_model = agent_config.model
                    
                    # Actualizar reputación EMA (en background, nunca bloquea)
                    try:
                        from backend.engine.reputation_manager import reputation_manager
                        from backend.engine.intervention_taxonomy import detect_intervention_type
                        
                        intervention_type = detect_intervention_type(
                            turn.response_received,
                            agent_config.role.value
                        )
                        
                        asyncio.create_task(reputation_manager.update_after_turn(
                            model=agent_config.model,
                            provider=agent_config.provider,
                            role=agent_config.role.value,
                            tokens_out=turn.tokens_out,
                            latency_ms=turn.latency_ms,
                            success=True,
                            intervention_type=intervention_type
                        ))
                    except Exception:
                        pass  # Silencioso - reputación no es crítica
                    
                    logger.info("sequential_debate.turn_complete",
                               session_id=session_id,
                               turn=idx,
                               tokens_out=turn.tokens_out,
                               latency_ms=turn.latency_ms)
                    
                except Exception as e:
                    logger.warning("sequential_debate.cloud_failed_fallback",
                                  session_id=session_id,
                                  turn=idx,
                                  agent=agent_config.name,
                                  error=str(e))
                    
                    # Fallback: Usar modelo local si cloud falla
                    if agent_config.node == "CLOUD":
                        logger.info("sequential_debate.using_fallback",
                                   session_id=session_id,
                                   turn=idx,
                                   fallback_model="llama3.2:latest")
                        
                        # Crear agente fallback local - asegurar role tiene valor
                        fallback_role = agent_config.role if hasattr(agent_config, 'role') else AgentRole.REFINER
                        logger.info("sequential_debate.fallback_creating", 
                                   session_id=session_id, 
                                   turn=idx,
                                   fallback_role=fallback_role.value if hasattr(fallback_role, 'value') else str(fallback_role))
                        fallback_agent = DebateAgent(
                            id=f"{agent_config.id}_fallback",
                            name=f"{agent_config.name} (Fallback Local)",
                            role=fallback_role,
                            node="LOCAL",
                            engine="ollama",
                            model="llama3.2:latest",
                            provider="meta",
                            system_prompt=agent_config.system_prompt + "\n\n[Nota: Actúas como respaldo local debido a indisponibilidad del servicio cloud]",
                            temperature=agent_config.temperature,
                            max_tokens=agent_config.max_tokens
                        )
                        
                        try:
                            response = await self._run_local_agent(
                                fallback_agent, 
                                full_prompt,
                                on_model_unload
                            )
                            turn.response_received = response["text"]
                            turn.tokens_in = response["tokens_in"]
                            turn.tokens_out = response["tokens_out"]
                            turn.latency_ms = response["latency_ms"]
                            turn.status = "completed (fallback)"
                            turn.agent = fallback_agent  # Actualizar agente usado
                            turn.completed_at = datetime.now()
                            
                            # Actualizar también en base de datos local para Supabase sync
                            try:
                                async with AsyncSessionLocal() as db_session:
                                    from sqlalchemy import update
                                    await db_session.execute(
                                        update(SequentialDebateTurn)
                                        .where(SequentialDebateTurn.debate_id == session_id)
                                        .where(SequentialDebateTurn.turn_number == turn.turn_number)
                                        .values(
                                            agent_id=fallback_agent.id,
                                            agent_name=fallback_agent.name,
                                            agent_role=fallback_agent.role.value,
                                            model=fallback_agent.model,
                                            provider=fallback_agent.provider,
                                            node=fallback_agent.node,
                                            engine=fallback_agent.engine,
                                            response_received=turn.response_received,
                                            tokens_in=turn.tokens_in,
                                            tokens_out=turn.tokens_out,
                                            latency_ms=turn.latency_ms,
                                            status=turn.status,
                                            completed_at=turn.completed_at
                                        )
                                    )
                                    await db_session.commit()
                                    logger.info("sequential_debate.fallback_db_updated",
                                               session_id=session_id,
                                               turn=idx)
                            except Exception as db_update_error:
                                logger.error("sequential_debate.fallback_db_update_failed",
                                            session_id=session_id,
                                            turn=idx,
                                            error=str(db_update_error))
                            
                            logger.info("sequential_debate.fallback_success",
                                       session_id=session_id,
                                       turn=idx,
                                       tokens_out=turn.tokens_out)
                            
                        except Exception as fallback_error:
                            turn.status = "failed"
                            turn.response_received = f"[ERROR Cloud: {str(e)}]\n[ERROR Fallback: {str(fallback_error)}]"
                            logger.error("sequential_debate.fallback_failed",
                                        session_id=session_id,
                                        turn=idx,
                                        error=str(fallback_error))
                    else:
                        turn.status = "failed"
                        turn.response_received = f"[ERROR: {str(e)}]"
                        logger.error("sequential_debate.turn_failed",
                                    session_id=session_id,
                                    turn=idx,
                                    error=str(e))
                
                if on_turn_complete:
                    on_turn_complete(turn)
                
                session.turns.append(turn)
                
                # Evaluar convergencia cada 2 turnos (early stop)
                if idx % 2 == 0 and idx >= 2:
                    try:
                        # Construir síntesis parcial para evaluación
                        completed_turns = [t for t in session.turns if t.status == "completed"]
                        if len(completed_turns) >= 2:
                            # Simular síntesis local desde turnos completados
                            local_synthesis_parts = []
                            for t in completed_turns[-2:]:  # Últimos 2 turnos
                                local_synthesis_parts.append(t.response_received)
                            local_synthesis = "\n\n".join(local_synthesis_parts)
                            
                            # Evaluar convergencia
                            convergence_result = self.convergence_evaluator.evaluate(
                                local_synthesis=local_synthesis,
                                cloud_synthesis="",  # Solo local en sequential
                                round_number=idx,
                                max_rounds=len(agents_config)
                            )
                            
                            logger.info("sequential_debate.convergence_evaluated",
                                       session_id=session_id,
                                       round=idx,
                                       should_stop=convergence_result.should_stop,
                                       consensus_level=convergence_result.consensus_level)
                            
                            if convergence_result.should_stop:
                                logger.info("sequential_debate.early_stop",
                                           session_id=session_id,
                                           round=idx,
                                           reason=convergence_result.consensus_level)
                                session.convergence_level = convergence_result.consensus_level
                                session.consensus_score = convergence_result.similarity_score
                                logger.info("sequential_debate.breaking_loop", session_id=session_id)
                                break
                    except Exception as e:
                        logger.error("sequential_debate.convergence_exception",
                                    session_id=session_id,
                                    error=str(e),
                                    error_type=type(e).__name__)
                
                # Persistir turno en base de datos
                try:
                    async with AsyncSessionLocal() as db_session:
                        # Asegurar que agent_role siempre tenga valor
                        agent_role_value = turn.agent.role.value if hasattr(turn.agent.role, 'value') else str(turn.agent.role)
                        logger.debug("sequential_debate.saving_turn_db",
                                    session_id=session_id,
                                    turn=turn.turn_number,
                                    agent_role=agent_role_value)
                        
                        db_turn = SequentialDebateTurn(
                            debate_id=session_id,
                            turn_number=turn.turn_number,
                            agent_id=turn.agent.id,
                            agent_name=turn.agent.name,
                            agent_role=agent_role_value,
                            model=turn.agent.model,
                            provider=turn.agent.provider,
                            node=turn.agent.node,
                            engine=turn.agent.engine,
                            prompt_sent=turn.prompt_sent,
                            response_received=turn.response_received,
                            tokens_in=turn.tokens_in,
                            tokens_out=turn.tokens_out,
                            latency_ms=turn.latency_ms,
                            status=turn.status,
                            started_at=turn.started_at,
                            completed_at=turn.completed_at
                        )
                        db_session.add(db_turn)
                        await db_session.commit()
                        logger.debug("sequential_debate.turn_saved_db",
                                    session_id=session_id,
                                    turn=turn.turn_number)
                except Exception as e:
                    logger.error("sequential_debate.turn_db_error",
                                session_id=session_id,
                                turn=turn.turn_number,
                                error=str(e))
                
                # Pequeña pausa entre turnos
                await asyncio.sleep(1)
            
            logger.info("sequential_debate.for_loop_finished", session_id=session_id, iterations_completed=idx)
            
            # Ejecutar Tribunal de Magistrados (si hay suficientes turnos completados)
            tribunal_result = None
            completed_turns = [t for t in session.turns if t.status == "completed"]
            
            if len(completed_turns) >= 2:
                logger.info("sequential_debate.tribunal_call_start", session_id=session_id, completed_turns=len(completed_turns))
                try:
                    async with AsyncSessionLocal() as db_session:
                        tribunal_result = await self._run_tribunal(session, db_session)
                        logger.info("sequential_debate.tribunal_call_completed", session_id=session_id)
                        if tribunal_result:
                            session.tribunal_verdict = tribunal_result
                            session.consensus_score = (tribunal_result.get("evidence_score", 50) + 
                                                     tribunal_result.get("risk_score", 50) + 
                                                     tribunal_result.get("alignment_score", 50)) / 3
                            session.convergence_level = "CONSENSUS_REACHED" if tribunal_result.get("consensus_reached") else "PARTIAL_CONSENSUS"
                except Exception as e:
                    logger.error("sequential_debate.tribunal_failed", session_id=session_id, error=str(e))
            else:
                logger.warning("sequential_debate.tribunal_skipped", session_id=session_id, reason="insufficient_completed_turns", completed=len(completed_turns))
            
            # Generar veredicto final
            if tribunal_result and tribunal_result.get("verdict_text"):
                session.final_verdict = tribunal_result["verdict_text"]
            else:
                session.final_verdict = self._generate_verdict(session)
            
            # Generar reporte estructurado JSON (v2.1)
            try:
                session.structured_report = await self._generate_structured_report(session)
                logger.info("sequential_debate.structured_report_generated", session_id=session_id)
            except Exception as e:
                logger.error("sequential_debate.structured_report_failed", error=str(e))
                
            session.status = "completed"
            session.completed_at = datetime.now()
            
            # Guardar archivo de transcripción
            transcript_path = await self._save_transcript(session)
            
            # Actualizar registro en BD con path y totales
            try:
                async with AsyncSessionLocal() as db_session:
                    db_debate = await db_session.get(SequentialDebate, session_id)
                    if db_debate:
                        db_debate.status = "completed"
                        db_debate.total_tokens_in = sum(t.tokens_in for t in session.turns)
                        db_debate.total_tokens_out = sum(t.tokens_out for t in session.turns)
                        db_debate.total_latency_ms = sum(t.latency_ms for t in session.turns)
                        db_debate.final_verdict = session.final_verdict
                        db_debate.structured_report = session.structured_report
                        db_debate.transcript_path = transcript_path
                        db_debate.completed_at = datetime.now()
                        await db_session.commit()
                        logger.info("sequential_debate.db_finalized",
                                   session_id=session_id,
                                   transcript_path=transcript_path)
            except Exception as e:
                logger.error("sequential_debate.final_db_error",
                            session_id=session_id,
                            error=str(e))
            
            logger.info("sequential_debate.completed",
                       session_id=session_id,
                       total_turns=len(session.turns),
                       total_tokens=sum(t.tokens_out for t in session.turns),
                       transcript_path=transcript_path)
            
            # Sincronización asíncrona con Supabase (usando HybridMemoryV2)
            try:
                from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2
                hybrid_mem = get_hybrid_memory_v2()
                asyncio.create_task(hybrid_mem.enqueue_sync(session, session_id, mode))
            except Exception:
                # Fallback: usar método legacy si existe
                try:
                    asyncio.create_task(self._sync_to_supabase(session, session_id, mode))
                except Exception:
                    pass  # Silencioso, mode))
            
        except Exception as e:
            session.status = "failed"
            logger.error("sequential_debate.outer_exception",
                        session_id=session_id,
                        error=str(e),
                        error_type=type(e).__name__)
            # Actualizar estado en BD
            try:
                async with AsyncSessionLocal() as db_session:
                    db_debate = await db_session.get(SequentialDebate, session_id)
                    if db_debate:
                        db_debate.status = "failed"
                        await db_session.commit()
            except:
                pass
            logger.error("sequential_debate.failed",
                        session_id=session_id,
                        error=str(e))
        
        return session
    
    async def _run_local_agent(
        self,
        agent: DebateAgent,
        prompt: str,
        on_model_unload: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, Any]:
        """Ejecuta agente local con Ollama"""
        
        start_time = datetime.now()
        engine_type = EngineType(agent.engine)
        
        # El modelo ya debe estar cargado en Ollama del Worker
        # Ollama lo cargará automáticamente al primer uso
        # y con keep_alive:0 se descargará tras inactividad
        
        response_parts = []
        tokens_out = 0
        
        async for token in self.local_manager.generate(
            engine_type=engine_type,
            model=agent.model,
            prompt=prompt,
            system=None,  # Ya incluido en prompt
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            stream=True
        ):
            response_parts.append(token)
            tokens_out += 1
        
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Callback: modelo descargado (virtualmente, Ollama maneja el keep_alive)
        if on_model_unload:
            on_model_unload(agent.model, agent.provider)
        
        return {
            "text": "".join(response_parts),
            "tokens_in": len(prompt.split()),  # Aproximación
            "tokens_out": tokens_out,
            "latency_ms": latency_ms
        }
    
    async def _run_cloud_agent(
        self,
        agent: DebateAgent,
        prompt: str
    ) -> Dict[str, Any]:
        """Ejecuta agente cloud vía OpenRouter"""
        
        if not self.openrouter:
            raise RuntimeError("OpenRouter not configured")
        
        start_time = datetime.now()
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response_parts = []
        tokens_out = 0
        
        async for token in self.openrouter.chat_completion(
            model=agent.model,
            messages=messages,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            stream=True
        ):
            response_parts.append(token)
            tokens_out += 1
        
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        response_text = "".join(response_parts)
        
        # Verificar si se generó contenido
        if not response_text.strip() or tokens_out == 0:
            raise RuntimeError(f"Cloud agent {agent.model} returned empty response (no credits or model unavailable)")
        
        return {
            "text": response_text,
            "tokens_in": len(prompt.split()),
            "tokens_out": tokens_out,
            "latency_ms": latency_ms
        }
    
    def _generate_verdict(self, session: DebateSession) -> str:
        """Genera un veredicto final del debate"""
        
        verdict_lines = [
            f"# VEREDICTO DEL SYNAPSE COUNCIL",
            f"## Tema: {session.topic}",
            "",
            "### Participantes"
        ]
        
        for turn in session.turns:
            verdict_lines.append(
                f"- **{turn.agent.name}** ({turn.agent.role.value}): "
                f"{turn.agent.model} ({turn.agent.provider})"
            )
        
        verdict_lines.extend([
            "",
            "### Resumen del Debate",
            ""
        ])
        
        # Extraer puntos clave de cada turno (primeras 200 chars)
        for turn in session.turns:
            if turn.status == "completed":
                preview = turn.response_received[:200].replace('\n', ' ')
                verdict_lines.append(
                    f"**{turn.agent.role.value.upper()}** ({turn.agent.provider}): {preview}..."
                )
        
        verdict_lines.extend([
            "",
            "---",
            "*Veredicto emitido por el Tribunal de Magistrados del Synapse Council v2.0*"
        ])
        
        return "\n".join(verdict_lines)
    
    async def _run_tribunal(
        self,
        session: DebateSession,
        db_session: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Ejecuta el Tribunal de Magistrados sobre el debate completado.
        
        Retorna dict con scores o None si falla.
        """
        try:
            # Filtrar turnos completados (mínimo 2)
            completed_turns = [t for t in session.turns if t.status == "completed"]
            
            if len(completed_turns) < 2:
                return None
            
            # Construir síntesis local desde turnos
            local_synthesis_parts = []
            for turn in completed_turns:
                local_synthesis_parts.append(
                    f"### {turn.agent.name} ({turn.agent.role.value})\n"
                    f"{turn.response_received}"
                )
            local_synthesis = "\n\n".join(local_synthesis_parts)
            
            # Para debate secuencial, cloud_synthesis es vacío (solo local)
            cloud_synthesis = ""
            
            # Llamar al Tribunal
            verdict = await self.tribunal.issue_verdict(
                session_id=session.id,
                round_id=session.id,  # Usar session_id como round_id
                round_number=1,
                query=session.topic,
                local_synthesis=local_synthesis,
                cloud_synthesis=cloud_synthesis,
                db_session=db_session,
                on_event=None  # Sin callbacks por ahora
            )
            
            logger.info("sequential_debate.tribunal_verdict_received",
                       session_id=session.id,
                       has_verdict_text=bool(verdict.verdict_text if verdict else False),
                       consensus_reached=verdict.consensus_reached if verdict else None)
            
            # Retornar dict serializable
            return {
                "verdict_text": verdict.verdict_text,
                "consensus_reached": verdict.consensus_reached,
                "iterations_required": verdict.iterations_required,
                "evidence_score": verdict.evidence_score,
                "risk_score": verdict.risk_score,
                "alignment_score": verdict.alignment_score,
                "dissent_areas": verdict.dissent_areas
            }
            
        except Exception as e:
            logger.error("sequential_debate.tribunal_failed",
                        session_id=session.id,
                        error=str(e),
                        error_type=type(e).__name__)
            return None
            
    async def _generate_structured_report(self, session: DebateSession) -> Dict[str, Any]:
        """
        Genera un informe estructurado JSON resumiendo el debate.
        Utiliza un modelo local rápido para la extracción.
        """
        logger.info("sequential_debate.generating_structured_report", session_id=session.id)
        
        # Fallback básico siempre disponible
        fallback_report = {
            "summary": f"Debate sobre {session.topic} con {len(session.turns)} turnos.",
            "consensus_level": 50,
            "key_findings": [f"Turnos completados: {len([t for t in session.turns if t.status == 'completed'])}"],
            "risks_identified": [],
            "action_items": [],
            "generated_by": "fallback"
        }
        
        # Consolidar todo el debate
        history = []
        for t in session.turns:
            if t.status.startswith("completed"):
                history.append(f"Agente {t.agent.name}: {t.response_received[:500]}")
        
        full_text = "\n\n".join(history)
        
        prompt = f"""Analiza el siguiente debate y genera un objeto JSON con el resumen ejecutivo.
TEMA: {session.topic}

DEBATE:
{full_text}

INSTRUCCIONES CRÍTICAS:
1. RESPONDE ÚNICAMENTE CON UN OBJETO JSON VÁLIDO
2. NO incluyas texto antes o después del JSON
3. NO uses bloques de código ```json```
4. El JSON debe tener esta estructura exacta:
{{
  "summary": "Resumen de 2 párrafos",
  "consensus_level": 0-100 (int),
  "key_findings": ["punto 1", "punto 2"],
  "risks_identified": ["riesgo 1"],
  "action_items": ["acción 1"]
}}

JSON:"""

        try:
            # Usar Llama3 para la estructuración
            response_text = ""
            async for token in self.local_manager.generate(
                engine_type=EngineType.OLLAMA,
                model="llama3.2:latest",
                prompt=prompt,
                temperature=0.1,
                max_tokens=800
            ):
                response_text += token
            
            # Extraer JSON de la respuesta - manejar múltiples formatos
            import re
            
            # Intentar 1: Buscar JSON directo
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            # Intento 2: Si hay ```json``` bloques, extraer el contenido
            if not json_match:
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1) if json_match.lastindex else json_match.group(0)
                try:
                    report_data = json.loads(json_str)
                    report_data["generated_by"] = "llama3.2:latest"
                    logger.info("sequential_debate.structured_report.parsed_successfully", session_id=session.id)
                    return report_data
                except json.JSONDecodeError as je:
                    logger.error("sequential_debate.structured_report.json_parse_error", 
                                 session_id=session.id, error=str(je), text_preview=json_str[:200])
                    return fallback_report
            
            logger.warning("sequential_debate.structured_report.no_json_found", session_id=session.id, response_preview=response_text[:200])
            return fallback_report
        except Exception as e:
            logger.error("sequential_debate.structured_report.exception", session_id=session.id, error=str(e))
            return fallback_report

    async def _save_transcript(self, session: DebateSession) -> str:
        """Guarda la transcripción completa del debate en archivo"""
        
        filename = f"debate_{session.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(TRANSCRIPTS_DIR, filename)
        
        lines = [
            f"# TRANSCRIPCIÓN DEL DEBATE: {session.topic}",
            "",
            f"**Session ID:** `{session.id}`",
            f"**Estado:** {session.status}",
            f"**Iniciado:** {session.created_at}",
            f"**Completado:** {session.completed_at}",
            "",
            "## Estadísticas",
            f"- **Total Turns:** {len(session.turns)}",
            f"- **Tokens In:** {sum(t.tokens_in for t in session.turns):,}",
            f"- **Tokens Out:** {sum(t.tokens_out for t in session.turns):,}",
            f"- **Tiempo Total:** {sum(t.latency_ms for t in session.turns)/1000:.1f}s",
            "",
            "="*80,
            ""
        ]
        
        # Detalle de cada turno
        for turn in session.turns:
            lines.extend([
                f"## Turno {turn.turn_number}: {turn.agent.name}",
                "",
                f"**Rol:** {turn.agent.role.value}",
                f"**Modelo:** `{turn.agent.model}`",
                f"**Provider:** {turn.agent.provider}",
                f"**Nodo:** {turn.agent.node}",
                f"**Engine:** {turn.agent.engine}",
                f"**Estado:** {turn.status}",
                f"**Tokens:** {turn.tokens_out} | **Tiempo:** {turn.latency_ms}ms",
                "",
                "### Prompt Enviado",
                "```",
                turn.prompt_sent[:500] + "..." if len(turn.prompt_sent) > 500 else turn.prompt_sent,
                "```",
                "",
                "### Respuesta",
                turn.response_received,
                "",
                "---",
                ""
            ])
        
        # Veredicto final
        if session.final_verdict:
            lines.extend([
                "",
                session.final_verdict,
                ""
            ])
        
        # Guardar archivo
        content = "\n".join(lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("sequential_debate.transcript_saved",
                   session_id=session.id,
                   filepath=filepath,
                   size_bytes=len(content))
        
        return filepath
    
    async def get_debate_from_db(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recupera un debate completo de la base de datos"""
        try:
            async with AsyncSessionLocal() as db_session:
                from sqlalchemy import select
                
                # Obtener debate
                result = await db_session.execute(
                    select(SequentialDebate).where(SequentialDebate.id == session_id)
                )
                debate = result.scalar_one_or_none()
                
                if not debate:
                    return None
                
                # Obtener turns
                turns_result = await db_session.execute(
                    select(SequentialDebateTurn)
                    .where(SequentialDebateTurn.debate_id == session_id)
                    .order_by(SequentialDebateTurn.turn_number)
                )
                turns = turns_result.scalars().all()
                
                return {
                    "id": debate.id,
                    "topic": debate.topic,
                    "mode": debate.mode,
                    "status": debate.status,
                    "total_tokens_in": debate.total_tokens_in,
                    "total_tokens_out": debate.total_tokens_out,
                    "total_latency_ms": debate.total_latency_ms,
                    "final_verdict": debate.final_verdict,
                    "transcript_path": debate.transcript_path,
                    "created_at": debate.created_at,
                    "completed_at": debate.completed_at,
                    "turns": [
                        {
                            "turn_number": t.turn_number,
                            "agent_name": t.agent_name,
                            "agent_role": t.agent_role,
                            "model": t.model,
                            "provider": t.provider,
                            "node": t.node,
                            "response_preview": t.response_received[:200] + "..." if len(t.response_received) > 200 else t.response_received,
                            "tokens_in": t.tokens_in,
                            "tokens_out": t.tokens_out,
                            "latency_ms": t.latency_ms,
                            "status": t.status
                        }
                        for t in turns
                    ]
                }
        except Exception as e:
            logger.error("sequential_debate.db_read_error",
                        session_id=session_id,
                        error=str(e))
            return None
    
    async def list_debates_from_db(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista debates históricos de la base de datos"""
        try:
            async with AsyncSessionLocal() as db_session:
                from sqlalchemy import select, desc
                
                result = await db_session.execute(
                    select(SequentialDebate)
                    .order_by(desc(SequentialDebate.created_at))
                    .limit(limit)
                )
                debates = result.scalars().all()
                
                return [
                    {
                        "id": d.id,
                        "topic": d.topic,
                        "mode": d.mode,
                        "status": d.status,
                        "total_turns": d.total_turns,
                        "total_tokens_out": d.total_tokens_out,
                        "transcript_path": d.transcript_path,
                        "created_at": d.created_at,
                        "completed_at": d.completed_at
                    }
                    for d in debates
                ]
        except Exception as e:
            logger.error("sequential_debate.db_list_error", error=str(e))
            return []
    
    async def _sync_to_supabase(self, session: DebateSession, session_id: str, mode: str = "local_only"):
        """Sincroniza debate con Supabase en background"""
        try:
            # Preparar datos para sincronización
            debate_data = {
                "id": session_id,
                "topic": session.topic,
                "mode": mode,  # Dinámico según parámetro
                "status": session.status,
                "total_turns": len(session.turns),
                "total_tokens_in": sum(t.tokens_in for t in session.turns),
                "total_tokens_out": sum(t.tokens_out for t in session.turns),
                "total_latency_ms": sum(t.latency_ms for t in session.turns),
                "final_verdict": session.final_verdict,
                "created_at": session.created_at,
                "completed_at": session.completed_at,
                "turns": [
                    {
                        "id": f"{session_id}_turn_{t.turn_number}",
                        "debate_id": session_id,
                        "turn_number": t.turn_number,
                        "agent_id": t.agent.id,
                        "agent_name": t.agent.name,
                        "agent_role": t.agent.role.value,
                        "model": t.agent.model,
                        "provider": t.agent.provider,
                        "node": t.agent.node,
                        "engine": t.agent.engine,
                        "prompt_sent": t.prompt_sent[:10000],  # Limitar
                        "response_received": t.response_received[:20000],  # Limitar
                        "tokens_in": t.tokens_in,
                        "tokens_out": t.tokens_out,
                        "latency_ms": t.latency_ms,
                        "status": t.status,
                        "started_at": t.started_at,
                        "completed_at": t.completed_at
                    }
                    for t in session.turns
                ]
            }
            
            # Sincronizar
            result = await supabase_service.sync_debate(debate_data)
            
            if result.get("synced"):
                logger.info("sequential_debate.supabase_synced",
                           session_id=session_id,
                           supabase_url=result.get("supabase_url"))
            else:
                logger.warning("sequential_debate.supabase_failed",
                            session_id=session_id,
                            error=result.get("error"))
                            
        except Exception as e:
            logger.error("sequential_debate.supabase_exception",
                        session_id=session_id,
                        error=str(e))
    
    def get_session(self, session_id: str) -> Optional[DebateSession]:
        """Obtiene una sesión de debate activa"""
        return self.active_sessions.get(session_id)
    
    def list_sessions(self) -> List[DebateSession]:
        """Lista todas las sesiones de debate"""
        return list(self.active_sessions.values())


# Configuraciones predefinidas de debates
def get_standard_debate_config(topic: str) -> List[DebateAgent]:
    """Configuración estándar: 3 locales + 1 cloud"""
    return [
        # 1. Análisis inicial - Meta (llama3)
        DebateAgent(
            id="analyst_llama3",
            name="Analista Meta",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3.2:latest",
            provider="meta",
            system_prompt="Analiza el tema propuesto desde una perspectiva técnica y estructurada. "
                        "Identifica los puntos clave, supuestos y posibles enfoques. "
                        "Responde en español, máximo 300 palabras.",
            temperature=0.7,
            max_tokens=500
        ),
        
        # 2. Crítica - Mistral AI
        DebateAgent(
            id="critic_mistral",
            name="Crítico Mistral",
            role=AgentRole.CRITIC,
            node="LOCAL",
            engine="ollama",
            model="mistral:7b",
            provider="mistral",
            system_prompt="Examina críticamente el análisis anterior. Identifica debilidades lógicas, "
                        "supuestos no verificados y alternativas no consideradas. "
                        "Sé constructivo pero riguroso. Responde en español, máximo 300 palabras.",
            temperature=0.8,
            max_tokens=500
        ),
        
        # 3. Síntesis - Alibaba (Qwen)
        DebateAgent(
            id="synth_qwen",
            name="Sintetizador Qwen",
            role=AgentRole.SYNTHESIZER,
            node="LOCAL",
            engine="ollama",
            model="qwen2.5:3b",
            provider="alibaba",
            system_prompt="Sintetiza los argumentos presentados hasta ahora. Encuentra puntos de "
                        "acuerdo y desacuerdo. Propone un marco integrador. "
                        "Responde en español, máximo 300 palabras.",
            temperature=0.6,
            max_tokens=500
        ),
        
        # 4. Refinamiento - OpenRouter (Cloud)
        DebateAgent(
            id="refiner_cloud",
            name="Refinador Cloud",
            role=AgentRole.REFINER,
            node="CLOUD",
            engine="openrouter",
            model="anthropic/claude-3.5-haiku",
            provider="anthropic",
            system_prompt="Refina y mejora la síntesis anterior. Considera perspectivas adicionales "
                        "y elabora una conclusión bien fundamentada. "
                        "Responde en español, máximo 400 palabras.",
            temperature=0.5,
            max_tokens=600
        )
    ]


def get_local_only_config(topic: str) -> List[DebateAgent]:
    """Configuración solo local: 4 modelos distintos"""
    return [
        DebateAgent(
            id="analyst_llama3",
            name="Analista Meta (Llama3)",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3.2:latest",
            provider="meta",
            system_prompt="Análisis técnico profundo del tema. Enfoque práctico y estructurado. "
                        "Máximo 300 palabras.",
            temperature=0.7
        ),
        DebateAgent(
            id="critic_mistral",
            name="Crítico Mistral",
            role=AgentRole.CRITIC,
            node="LOCAL",
            engine="ollama",
            model="mistral:7b",
            provider="mistral",
            system_prompt="Crítica constructiva y rigurosa del análisis. Identificar debilidades. "
                        "Máximo 300 palabras.",
            temperature=0.8
        ),
        DebateAgent(
            id="synth_qwen",
            name="Sintetizador Qwen (Alibaba)",
            role=AgentRole.SYNTHESIZER,
            node="LOCAL",
            engine="ollama",
            model="qwen2.5:3b",
            provider="alibaba",
            system_prompt="Síntesis integradora de todos los argumentos. Enfoque oriental pragmatico. "
                        "Máximo 300 palabras.",
            temperature=0.6
        ),
        DebateAgent(
            id="refiner_deepseek",
            name="Refinador DeepSeek",
            role=AgentRole.REFINER,
            node="LOCAL",
            engine="ollama",
            model="deepseek-r1:7b",
            provider="deepseek",
            system_prompt="Refinamiento final con reasoning. Considera implicaciones profundas. "
                        "Máximo 350 palabras.",
            temperature=0.5
        )
    ]
def get_cloud_ollama_config(topic: str) -> List[DebateAgent]:
    """Configuración que usa modelos grandes vía Ollama Cloud en el Master"""
    return [
        DebateAgent(
            id="cloud_analyst",
            name="Analista Senior (Cloud)",
            role=AgentRole.ANALYST,
            node="CLOUD",
            engine="ollama",
            model="llama3:70b-cloud",  # Modelo grande en la nube de Ollama
            provider="meta",
            system_prompt="Realiza un análisis exhaustivo y profundo del tema. Al ser un modelo de alta capacidad, "
                        "enfócate en matices técnicos y conexiones complejas. Responde en español.",
            temperature=0.4,
            max_tokens=1000
        ),
        DebateAgent(
            id="cloud_critic",
            name="Crítico Experto (Cloud)",
            role=AgentRole.CRITIC,
            node="CLOUD",
            engine="ollama",
            model="mistral-large-cloud",
            provider="mistral",
            system_prompt="Ejerce una crítica rigurosa sobre el análisis previo. Busca fallos estructurales, "
                        "sesgos cognitivos y omisiones técnicas. Responde en español.",
            temperature=0.6,
            max_tokens=800
        ),
        DebateAgent(
            id="cloud_synth",
            name="Sintetizador Maestro (Cloud)",
            role=AgentRole.SYNTHESIZER,
            node="CLOUD",
            engine="ollama",
            model="llama3:70b-cloud",
            provider="meta",
            system_prompt="Sintetiza las posturas enfrentadas. Genera una resolución de alto nivel que "
                        "integre la crítica y el análisis original. Responde en español.",
            temperature=0.3,
            max_tokens=1200
        )
    ]
