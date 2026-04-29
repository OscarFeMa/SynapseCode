"""
Synapse Council v2.2 - UltraDebateController
Orquestador de alta densidad con cruce recursivo y agentes multinodo.
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import structlog

from backend.engine.agent_orchestrator import AgentOrchestrator, AgentConfig
from backend.engine.sequential_debate_controller import AgentRole, DebateTurn, DebateSession
from backend.database.local_db import AsyncSessionLocal
from backend.database.models import SequentialDebate

logger = structlog.get_logger()

class UltraDebateController:
    """
    Controlador de debate de "Espejo Cruzado" (Ultra-Crossing).
    Ejecuta agentes en paralelo por etapas, cruzando contextos de Master y Worker.
    """
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.active_sessions: Dict[str, DebateSession] = {}

    async def create_ultra_debate(self, topic: str) -> str:
        """Inicia un debate de ultra-alta densidad con ID autogenerado"""
        session_id = str(uuid.uuid4())
        return await self.create_ultra_debate_with_id(session_id, topic)

    async def create_ultra_debate_with_id(self, session_id: str, topic: str) -> str:
        """Inicia un debate de ultra-alta densidad con ID proporcionado"""
        session = DebateSession(id=session_id, topic=topic)
        session.status = "running"
        self.active_sessions[session_id] = session
        
        # 1. Definir Etapas y Agentes (Solo Groq por ahora - Gemini tiene problemas de modelo)
        self.stages = [
            {
                "name": "Propuestas Iniciales",
                "agents": [
                    AgentConfig("proposer_groq_1", "CLOUD", "groq", "llama-3.3-70b-versatile", "Proponente Maestro (Groq)"),
                    AgentConfig("proposer_groq_2", "CLOUD", "groq", "mixtral-8x7b-32768", "Proponente Alternativo (Groq)")
                ]
            },
            {
                "name": "Expansión y Refinamiento",
                "agents": [
                    AgentConfig("refiner_groq_1", "CLOUD", "groq", "llama-3.3-70b-versatile", "Refinador Analítico (Groq)"),
                    AgentConfig("refiner_groq_2", "CLOUD", "groq", "gemma-7b-it", "Refinador Técnico (Groq)")
                ]
            },
            {
                "name": "Crítica Cruzada",
                "agents": [
                    AgentConfig("critic_groq_1", "CLOUD", "groq", "llama-3.3-70b-versatile", "Crítico Superior (Groq)"),
                    AgentConfig("critic_groq_2", "CLOUD", "groq", "mixtral-8x7b-32768", "Crítico Alternativo (Groq)")
                ]
            },
            {
                "name": "Síntesis Final",
                "agents": [
                    AgentConfig("synthesizer_groq", "CLOUD", "groq", "llama-3.3-70b-versatile", "Sintetizador Maestro (Groq)")
                ]
            }
        ]

        logger.info("ultra_debate.start", session_id=session_id, topic=topic)
        
        try:
            async with AsyncSessionLocal() as db:
                for stage_idx, stage in enumerate(self.stages):
                    logger.info("ultra_debate.stage_start", stage=stage["name"], stage_idx=stage_idx, num_agents=len(stage["agents"]))
                    
                    # Construir prompt basado en el historial
                    logger.info("ultra_debate.building_context", session_id=session_id, turns_in_session=len(session.turns))
                    context = self._build_stage_context(session)
                    logger.info("ultra_debate.context_built", context_length=len(context))
                    
                    # Función helper para llamar a agente con su propia sesión
                    async def call_with_own_session(agent_cfg, s_prompt, u_prompt):
                        async with AsyncSessionLocal() as session:
                            return await self.orchestrator.call_agent(
                                session_id=session_id,
                                round_id=session_id,
                                round_number=stage_idx + 1,
                                phase=stage["name"],
                                config=agent_cfg,
                                system_prompt=s_prompt,
                                user_prompt=u_prompt,
                                db_session=session
                            )

                    # Preparar tareas
                    tasks = []
                    for agent_cfg in stage["agents"]:
                        system_prompt = self._get_dynamic_system_prompt(agent_cfg, stage["name"], stage_idx)
                        user_prompt = f"Tema: {topic}\n\nContexto del debate hasta ahora:\n{context}\n\nTu tarea: {stage['name']}"
                        tasks.append(call_with_own_session(agent_cfg, system_prompt, user_prompt))
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Filtrar excepciones de los resultados
                    valid_results = []
                    for r in results:
                        if isinstance(r, Exception):
                            logger.error("ultra_debate.agent_error", error=str(r))
                            from backend.engine.agent_orchestrator import AgentResult
                            valid_results.append(AgentResult(call_id="", slot="error", node="UNKNOWN", status="FAILED", error_message=str(r)))
                        else:
                            valid_results.append(r)
                    
                    results = valid_results
                    
                    # Guardar turnos en la sesión (para contexto acumulado)
                    for agent_cfg, result in zip(stage["agents"], results):
                        # Crear un objeto compatible con DebateAgent para el turno
                        from backend.engine.sequential_debate_controller import DebateAgent, AgentRole
                        
                        agent_obj = DebateAgent(
                            id=agent_cfg.slot,
                            name=agent_cfg.role_label,
                            role=AgentRole.ANALYST, # Simplificado para Ultra
                            node=agent_cfg.node,
                            engine=agent_cfg.engine,
                            model=agent_cfg.model,
                            provider=agent_cfg.engine, # Simplificado
                            system_prompt=self._get_dynamic_system_prompt(agent_cfg, stage["name"], stage_idx)
                        )

                        turn = DebateTurn(
                            turn_number=len(session.turns) + 1,
                            agent=agent_obj,
                            prompt_sent=topic,
                            response_received=result.response or "[Fallo]",
                            tokens_in=result.tokens_in,
                            tokens_out=result.tokens_out,
                            latency_ms=result.latency_ms,
                            status=result.status
                        )
                        session.turns.append(turn)
                
                session.status = "completed"
                session.completed_at = datetime.now()
                
                # Persistir sesión final
                await self._persist_session(session)
                
                # Actualizar en ultra_controller
                self.active_sessions[session_id] = session
                
                # Actualizar también en debate_controller si existe (para API)
                from backend.engine.sequential_debate_controller import SequentialDebateController
                try:
                    debate_ctrl = SequentialDebateController()
                    if session_id in debate_ctrl.active_sessions:
                        debate_ctrl.active_sessions[session_id] = session
                except:
                    pass  # Si falla, no es crítico
                
                return session_id
            
        except Exception as e:
            logger.error("ultra_debate.failed", session_id=session_id, error=str(e))
            session.status = "failed"
            return session_id

    def _build_stage_context(self, session: DebateSession) -> str:
        """Construye el resumen del debate para la siguiente etapa"""
        if not session.turns:
            return "Inicio del debate."
        
        lines = []
        for t in session.turns:
            lines.append(f"--- INTERVENCION DE {t.agent.name} ({t.agent.model}) ---")
            lines.append(t.response_received[:2000]) # Evitar context blowup
            lines.append("")
        return "\n".join(lines)

    def _get_dynamic_system_prompt(self, agent: AgentConfig, stage_name: str, stage_idx: int) -> str:
        """Genera el prompt de sistema dinámicamente"""
        base = f"Eres {agent.role_label}, un experto en el Synapse Council. "
        
        if "Propuesta" in stage_name:
            return base + "Tu objetivo es presentar una visión original y sólida sobre el tema. No te repitas."
        elif "Refinamiento" in stage_name:
            return base + "Tu objetivo es tomar las propuestas iniciales y elevar su calidad, corrigiendo errores y añadiendo profundidad."
        elif "Crítica" in stage_name:
            return base + "Tu objetivo es actuar como abogado del diablo. Busca fallos lógicos, sesgos y debilidades en lo dicho hasta ahora."
        elif "Síntesis" in stage_name:
            return base + "Tu objetivo es unificar todas las posturas en una resolución coherente y final."
        
        return base

    async def _persist_session(self, session: DebateSession):
        """Guarda el resultado en la base de datos local"""
        try:
            async with AsyncSessionLocal() as db:
                db_debate = SequentialDebate(
                    id=session.id,
                    topic=session.topic,
                    mode="ultra_crossing",
                    status=session.status,
                    total_turns=len(session.turns),
                    total_tokens_out=sum(t.tokens_out for t in session.turns),
                    created_at=session.created_at,
                    completed_at=session.completed_at
                )
                db.add(db_debate)
                await db.commit()
        except Exception as e:
            logger.error("ultra_debate.persistence_error", error=str(e))
