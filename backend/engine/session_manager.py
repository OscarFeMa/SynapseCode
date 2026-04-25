"""
Synapse Council v2.0 - Session Manager
Gestiona el ciclo de vida completo de una sesión de debate
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Tuple
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.engine.round_controller import RoundController
from backend.engine.convergence import ConvergenceEvaluator, ConvergenceResult
from backend.engine.reputation import ReputationManager
from backend.database.supabase_client import supabase_client
from backend.database.models import Session, Round, AgentCall, SystemEvent
from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class SessionManager:
    """
    Gestor de sesiones:
    - Crear sesión
    - Ejecutar rondas múltiples (Fase 2+)
    - Verificar convergencia
    - Finalizar con veredicto (Tribunal - Fase 2)
    """
    
    def __init__(self):
        self.round_controller = RoundController()
        self.convergence_evaluator = ConvergenceEvaluator()
        self.reputation_manager = ReputationManager()
    
    async def create_session(
        self,
        query: str,
        db_session: AsyncSession,
        title: Optional[str] = None,
        max_rounds: int = None,
        config: Optional[Dict] = None
    ) -> Session:
        """
        Crea una nueva sesión de debate
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Config por defecto
        session_config = config or {
            "max_rounds": max_rounds or settings.DEFAULT_MAX_ROUNDS,
            "cost_limit_usd": settings.DEFAULT_COST_LIMIT_USD,
            "auto_elevation": settings.AUTO_ELEVATION_ENABLED,
        }
        
        session = Session(
            id=session_id,
            title=title or f"Debate: {query[:50]}...",
            query=query,
            status="CREATED",
            max_rounds=session_config["max_rounds"],
            config_snapshot=session_config,  # Dict directo, SQLAlchemy JSON lo serializa
            node_origin=settings.NODE_ROLE,
            started_at=now,
            created_at=now,
        )
        
        db_session.add(session)
        await db_session.commit()
        
        logger.info(
            "session.created",
            session_id=session_id,
            query=query[:100],
            max_rounds=session_config["max_rounds"],
        )
        
        return session
    
    async def run_session(
        self,
        session_id: str,
        db_session: AsyncSession,
        on_event: Optional[Callable[[str, Any], None]] = None
    ) -> Session:
        """
        Ejecuta una sesión completa de debate con múltiples rondas (Fase 2+)
        Evalúa convergencia entre rondas y decide si continuar o detener.
        """
        # Obtener sesión
        result = await db_session.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status == "COMPLETED":
            raise ValueError(f"Session {session_id} already completed")
        
        # Actualizar estado
        session.status = "RUNNING"
        await db_session.commit()
        
        if on_event:
            on_event("session_started", {"session_id": session_id, "query": session.query})
        
        logger.info(
            "session.running",
            session_id=session_id,
            max_rounds=session.max_rounds,
        )
        
        # Historial de síntesis para evaluación de convergencia (stateless)
        syntheses_history: List[Tuple[str, str]] = []
        
        all_round_results = []
        final_tribunal_verdict = None
        
        try:
            for round_num in range(1, session.max_rounds + 1):
                logger.info(
                    "session.executing_round",
                    session_id=session_id,
                    round_number=round_num,
                    max_rounds=session.max_rounds,
                )
                
                if on_event:
                    on_event("round_start", {"round_number": round_num, "total_rounds": session.max_rounds})
                
                # Contexto de rondas previas (para rondas 2+)
                previous_context = None
                if round_num > 1 and all_round_results:
                    prev_result = all_round_results[-1]
                    # Generar contexto resumido
                    previous_context = self._build_round_context(prev_result)
                
                # Ejecutar ronda
                round_result = await self.round_controller.execute_round(
                    session_id=session_id,
                    round_number=round_num,
                    query=session.query,
                    db_session=db_session,
                    max_rounds=session.max_rounds,
                    previous_context=previous_context,
                    on_event=on_event
                )
                
                all_round_results.append(round_result)
                session.rounds_executed = round_num
                await db_session.commit()
                
                # Guardar veredicto del tribunal de la última ronda
                if round_result.get("tribunal_verdict"):
                    final_tribunal_verdict = round_result["tribunal_verdict"]
                
                # Evaluar convergencia (para decidir si continuar)
                synthesis_local = round_result["synthesis"].get("synth_local", "")
                synthesis_cloud = round_result["synthesis"].get("synth_cloud", "")
                
                if round_num < session.max_rounds and synthesis_local and synthesis_cloud:
                    convergence = self.convergence_evaluator.evaluate(
                        local_synthesis=synthesis_local,
                        cloud_synthesis=synthesis_cloud,
                        round_number=round_num,
                        max_rounds=session.max_rounds,
                        tribunal_verdict=round_result.get("tribunal_verdict"),
                        previous_syntheses=syntheses_history
                    )
                    
                    # Añadir al historial después de evaluar
                    syntheses_history.append((synthesis_local, synthesis_cloud))
                    
                    if on_event:
                        on_event("convergence_evaluated", {
                            "round_number": round_num,
                            "consensus_level": convergence.consensus_level,
                            "similarity_score": round(convergence.similarity_score, 2),
                            "should_stop": convergence.should_stop
                        })
                    
                    # Guardar en round
                    round_record_result = await db_session.execute(
                        select(Round).where(Round.id == round_result["round_id"])
                    )
                    round_record = round_record_result.scalar_one()
                    round_record.convergence_status = convergence.consensus_level
                    round_record.convergence_detail = convergence.detail
                    await db_session.commit()
                    
                    logger.info(
                        "convergence.result",
                        session_id=session_id,
                        round_number=round_num,
                        consensus_level=convergence.consensus_level,
                        should_stop=convergence.should_stop,
                    )
                    
                    # ¿Detener por convergencia?
                    if convergence.should_stop:
                        logger.info(
                            "session.stopping_by_convergence",
                            session_id=session_id,
                            round=round_num,
                            reason=convergence.consensus_level
                        )
                        break
            
            # Compilar resultado final con veredicto del Tribunal
            final_summary = self._compile_final_summary(
                all_round_results,
                final_tribunal_verdict
            )
            
            # Determinar nivel de consenso final
            consensus_level = "PARTIAL_CONSENSUS"
            if final_tribunal_verdict:
                if final_tribunal_verdict.get("consensus_reached"):
                    consensus_level = "CONSENSUS_REACHED"
                elif final_tribunal_verdict.get("evidence_score", 0) > 70:
                    consensus_level = "PARTIAL_CONSENSUS"
                else:
                    consensus_level = "DIVERGENT"
            
            session.final_summary = final_summary
            session.consensus_level = consensus_level
            session.tribunal_verdict = final_tribunal_verdict
            session.status = "COMPLETED"
            session.completed_at = datetime.utcnow()
            
            # Actualizar métricas
            await self._update_session_metrics(session, db_session)
            
            # (Commit aplazado hasta el final para atomicidad)
            
            # Actualizar reputación de agentes (Fase 5)
            if settings.AGENT_REPUTATION_ENABLED:
                try:
                    await self.reputation_manager.update_reputation_after_session(
                        session_id, db_session
                    )
                except Exception as e:
                    logger.error(
                        "reputation.update_failed",
                        session_id=session_id,
                        error=str(e)
                    )
            
            # Elevar a Supabase si cumple criterios (Fase 5)
            if settings.AUTO_ELEVATION_ENABLED and session.consensus_level in ["CONSENSUS_REACHED", "DIVERGENT"]:
                try:
                    elevation_reason = (
                        "Consenso significativo alcanzado" 
                        if session.consensus_level == "CONSENSUS_REACHED"
                        else "Divergencia notable requiere revisión humana"
                    )
                    
                    elevated_id = await supabase_client.elevate_verdict(
                        session_id=session_id,
                        query=session.query,
                        final_summary=session.final_summary or "",
                        consensus_level=session.consensus_level,
                        tribunal_verdict=session.tribunal_verdict or {},
                        rounds_executed=session.rounds_executed,
                        config_snapshot=session.config_snapshot or {},
                        elevation_reason=elevation_reason
                    )
                    
                    if elevated_id:
                        session.elevated_to_cloud = True
                        session.elevation_reason = elevation_reason
                        # No hacemos commit aquí todavía
                        
                except Exception as e:
                    logger.error(
                        "supabase.elevation_failed",
                        session_id=session_id,
                        error=str(e)
                    )
            
            logger.info(
                "session.completed",
                session_id=session_id,
                rounds=session.rounds_executed,
                consensus=session.consensus_level,
                tribunal_consensus=final_tribunal_verdict.get("consensus_reached") if final_tribunal_verdict else None
            )
            
            # ─── ÚNICO COMMIT FINAL ───
            await db_session.commit()
            
            if on_event:
                on_event("session_completed", {
                    "session_id": session_id,
                    "consensus_level": session.consensus_level,
                    "rounds": session.rounds_executed,
                    "tribunal_consensus": final_tribunal_verdict.get("consensus_reached") if final_tribunal_verdict else None
                })
            
            return session
            
        except Exception as e:
            session.status = "FAILED"
            session.completed_at = datetime.utcnow()
            await db_session.commit()
            
            # Registrar evento de error
            error_event = SystemEvent(
                id=str(uuid.uuid4()),
                session_id=session_id,
                event_type="SESSION_FAILED",
                severity="ERROR",
                message=f"Session execution failed: {str(e)}",
                detail={"error": str(e)},
            )
            db_session.add(error_event)
            await db_session.commit()
            
            logger.error(
                "session.failed",
                session_id=session_id,
                error=str(e),
            )
            raise
    
    async def get_session_detail(
        self,
        session_id: str,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Obtiene detalle completo de una sesión con todas sus rondas y llamadas
        """
        # Sesión
        result = await db_session.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return None
        
        # Rondas
        rounds_result = await db_session.execute(
            select(Round).where(Round.session_id == session_id)
        )
        rounds = rounds_result.scalars().all()
        
        # Agent calls
        calls_result = await db_session.execute(
            select(AgentCall).where(AgentCall.session_id == session_id)
        )
        calls = calls_result.scalars().all()
        
        # Organizar por fases
        calls_by_phase = {}
        for call in calls:
            phase = call.phase
            if phase not in calls_by_phase:
                calls_by_phase[phase] = []
            calls_by_phase[phase].append({
                "id": call.id,
                "slot": call.agent_slot,
                "node": call.node,
                "engine": call.engine,
                "model": call.model_name,
                "status": call.status,
                "tokens_in": call.tokens_in,
                "tokens_out": call.tokens_out,
                "latency_ms": call.latency_ms,
                "response_preview": call.response[:200] + "..." if call.response and len(call.response) > 200 else call.response,
            })
        
        return {
            "session": {
                "id": session.id,
                "title": session.title,
                "query": session.query,
                "status": session.status,
                "consensus_level": session.consensus_level,
                "rounds_executed": session.rounds_executed,
                "max_rounds": session.max_rounds,
                "final_summary": session.final_summary,
                "total_tokens_in": session.total_tokens_in,
                "total_tokens_out": session.total_tokens_out,
                "estimated_cost_usd": session.estimated_cost_usd,
                "created_at": session.created_at,
                "completed_at": session.completed_at,
            },
            "rounds": [
                {
                    "id": r.id,
                    "number": r.round_number,
                    "status": r.status,
                    "convergence_status": r.convergence_status,
                    "started_at": r.started_at,
                    "completed_at": r.completed_at,
                }
                for r in rounds
            ],
            "agent_calls": calls_by_phase,
        }
    
    async def _update_session_metrics(
        self,
        session: Session,
        db_session: AsyncSession
    ):
        """Calcula métricas agregadas de la sesión"""
        result = await db_session.execute(
            select(AgentCall).where(
                AgentCall.session_id == session.id,
                AgentCall.status == "COMPLETED"
            )
        )
        calls = result.scalars().all()
        
        total_in = sum(c.tokens_in or 0 for c in calls)
        total_out = sum(c.tokens_out or 0 for c in calls)
        
        session.total_tokens_in = total_in
        session.total_tokens_out = total_out
        
        # Estimación de costo (aproximada, varía por modelo)
        # Precios aproximados por 1K tokens
        price_per_1k = {
            "openrouter": 0.002,  # Variable, promedio
            "ollama": 0.0,        # Local = gratis
            "lm_studio": 0.0,
            "jan": 0.0,
            "web_agent": 0.0,
        }
        
        cost = 0.0
        for call in calls:
            engine_price = price_per_1k.get(call.engine, 0.002)
            cost += (call.tokens_in or 0) * engine_price / 1000
            cost += (call.tokens_out or 0) * engine_price / 1000
        
        session.estimated_cost_usd = round(cost, 4)
    
    async def list_sessions(
        self,
        db_session: AsyncSession,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Lista sesiones con filtros opcionales"""
        query = select(Session)
        
        if status:
            query = query.where(Session.status == status)
        
        query = query.order_by(Session.created_at.desc()).limit(limit).offset(offset)
        
        result = await db_session.execute(query)
        sessions = result.scalars().all()
        
        return [
            {
                "id": s.id,
                "title": s.title,
                "query": s.query[:100] + "..." if len(s.query) > 100 else s.query,
                "status": s.status,
                "consensus_level": s.consensus_level,
                "rounds_executed": s.rounds_executed,
                "created_at": s.created_at,
                "completed_at": s.completed_at,
            }
            for s in sessions
        ]
    
    def _build_round_context(self, round_result: Dict[str, Any]) -> str:
        """
        Construye contexto resumido de ronda previa para rondas posteriores.
        Limitado a ~1000 tokens aproximadamente.
        """
        context_parts = ["## Contexto de Ronda Anterior\n"]
        
        # Síntesis previas
        synth = round_result.get("synthesis", {})
        local_synth = synth.get("synth_local", "")[:400]
        cloud_synth = synth.get("synth_cloud", "")[:400]
        
        if local_synth:
            context_parts.append(f"**Síntesis Local previa:**\n{local_synth}...\n")
        if cloud_synth:
            context_parts.append(f"**Síntesis Cloud previa:**\n{cloud_synth}...\n")
        
        # Veredicto del tribunal si existe
        tribunal = round_result.get("tribunal_verdict")
        if tribunal:
            consensus = "alcanzado" if tribunal.get("consensus_reached") else "no alcanzado"
            context_parts.append(f"\n**Consenso Tribunal:** {consensus}")
            context_parts.append(f"(Evidencia: {tribunal.get('evidence_score', 0)}/100, Riesgo: {tribunal.get('risk_score', 0)}/100)\n")
        
        context_parts.append("\n**Instrucción:** En esta ronda, profundice específicamente en los puntos de disenso. No repita argumentos ya convergentes.")
        
        return "\n".join(context_parts)
    
    def _compile_final_summary(
        self,
        all_round_results: List[Dict[str, Any]],
        final_tribunal_verdict: Optional[Dict[str, Any]]
    ) -> str:
        """
        Compila el resumen final de la sesión con todas las rondas y el veredicto del Tribunal.
        """
        summary_parts = ["# VEREDICTO DEL SYNAPSE COUNCIL\n"]
        
        # Veredicto del Tribunal (si existe)
        if final_tribunal_verdict:
            summary_parts.append("## 🏛️ Veredicto del Tribunal de Magistrados\n")
            
            verdict_text = final_tribunal_verdict.get("verdict_text", "")
            # Extraer solo el veredicto final (hasta Fundamentos o similar)
            if "## Veredicto Final" in verdict_text:
                try:
                    verdict_section = verdict_text.split("## Veredicto Final")[1]
                    # Cortar en la siguiente sección principal
                    for separator in ["## Fundamentos", "## Pasos Accionables", "---"]:
                        if separator in verdict_section:
                            verdict_section = verdict_section.split(separator)[0]
                            break
                    summary_parts.append(verdict_section.strip()[:1500])
                except IndexError:
                    summary_parts.append(verdict_text[:1500])
            else:
                summary_parts.append(verdict_text[:1500])
            
            summary_parts.append("\n")
            
            # Metadata del tribunal
            summary_parts.append(f"\n**Estadísticas del Tribunal:**")
            summary_parts.append(f"- Consenso alcanzado: {'Sí' if final_tribunal_verdict.get('consensus_reached') else 'No'}")
            summary_parts.append(f"- Iteraciones PCO: {final_tribunal_verdict.get('iterations_required', 0)}")
            summary_parts.append(f"- Score Técnico: {final_tribunal_verdict.get('evidence_score', 0)}/100")
            summary_parts.append(f"- Score de Riesgo: {final_tribunal_verdict.get('risk_score', 0)}/100")
            summary_parts.append(f"- Score de Alineación: {final_tribunal_verdict.get('alignment_score', 0)}/100")
        
        # Resumen de rondas
        if len(all_round_results) > 1:
            summary_parts.append(f"\n\n## 📊 Proceso de Deliberación ({len(all_round_results)} rondas)")
            for i, round_result in enumerate(all_round_results, 1):
                tribunal = round_result.get("tribunal_verdict")
                if tribunal:
                    consensus_mark = "✅" if tribunal.get("consensus_reached") else "⚠️"
                    summary_parts.append(f"\n**Ronda {i}:** {consensus_mark} Evidencia={tribunal.get('evidence_score', 0)}, Riesgo={tribunal.get('risk_score', 0)}")
        
        summary_parts.append("\n\n---\n*Veredicto emitido por el Tribunal de Magistrados del Synapse Council v2.0*")
        
        return "\n".join(summary_parts)
