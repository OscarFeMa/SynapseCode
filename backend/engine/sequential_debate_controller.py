"""
Synapse Council v2.0 - Sequential Multi-Model Debate Controller
Debate secuencial con carga/descarga dinámica de modelos
"""

import asyncio
import hashlib
import json
import os
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.openrouter import OpenRouterClient
from backend.config import get_settings
from backend.database.local_db import AsyncSessionLocal
from backend.database.models import (
    PromptResponseCache,
    ReductioAbsurdumProof,
    SequentialDebate,
    SequentialDebateTurn,
)
from backend.engine.convergence import ConvergenceEvaluator
from backend.engine.debate_models import (
    AgentRole,
    CruzamientoCritico,
    DebateAgent,
    DebateSession,
    DebateTurn,
    IteracionDebate,
)
from backend.engine.intervention_taxonomy import detect_intervention_type
from backend.engine.local_engine_manager import EngineType, LocalEngineManager
from backend.engine.quality_monitor import evaluate_response
from backend.engine.reductio_absurdum import (
    AbsurdumProof,
    ComplacencyScan,
    get_reductio_absurdum_engine,
)
from backend.engine.reputation_unified import reputation_service
from backend.engine.role_matcher import RoleMatcher
from backend.engine.task_manager import (
    TaskConfig,
    submit_reputation_update,
    task_manager,
)
from backend.engine.tribunal import TribunalCouncil
from backend.engine.web_search_service import get_web_search_service
from backend.monitoring.prometheus import (
    record_debate_completed,
    record_prompt_cache_hit,
    record_prompt_cache_miss,
)

settings = get_settings()

# Lazy init del warehouse manager
_warehouse_manager = None


def _get_warehouse_manager():
    global _warehouse_manager
    if _warehouse_manager is None:
        from backend.database.warehouse import warehouse_manager

        _warehouse_manager = warehouse_manager
    return _warehouse_manager


logger = structlog.get_logger()

# Lazy init: solo se crea el servicio si SUPABASE_ENABLED=true y hay URL/key
_supabase_service = None


def _get_supabase_service():
    global _supabase_service
    if _supabase_service is None:
        from backend.services.supabase_sync import get_supabase_service

        _supabase_service = get_supabase_service()
    return _supabase_service


# Directorio para transcripts
TRANSCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "debates")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


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
        self._openrouter = None  # Lazy init
        self.active_sessions: dict[str, DebateSession] = {}
        self.tribunal = TribunalCouncil()
        self.convergence_evaluator = ConvergenceEvaluator()
        self.reductio_engine = get_reductio_absurdum_engine()  # Motor de reducción al absurdo
        # Configurar callback para persistir pruebas automaticamente
        self.reductio_engine.set_persist_callback(self._on_absurdum_proof_created)

    @property
    def openrouter(self):
        """OpenRouter client con lazy initialization"""
        if self._openrouter is None and settings.OPENROUTER_API_KEY:
            self._openrouter = OpenRouterClient()
        return self._openrouter

    def _find_next_preload_model(self, agents_config: list[DebateAgent], current_index: int) -> str | None:
        """Busca el próximo modelo local de Ollama distinto al turno actual para precarga."""
        current_model = agents_config[current_index].model if current_index < len(agents_config) else None
        for next_agent in agents_config[current_index + 1 :]:
            if next_agent.node == "LOCAL" and next_agent.engine == "ollama" and next_agent.model != current_model:
                return next_agent.model
        return None

    def _build_prompt_cache_key(self, agent: DebateAgent, prompt: str) -> tuple[str, str]:
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        raw_key = "|".join(
            [
                agent.node,
                agent.engine,
                agent.model,
                str(agent.temperature),
                str(agent.max_tokens),
                prompt_hash,
            ]
        )
        cache_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return cache_key, prompt_hash

    async def _get_cached_response(self, agent: DebateAgent, prompt: str) -> dict[str, Any] | None:
        cache_key, _ = self._build_prompt_cache_key(agent, prompt)
        async with AsyncSessionLocal() as db_session:
            cached = await db_session.scalar(
                select(PromptResponseCache).where(PromptResponseCache.cache_key == cache_key)
            )
            if not cached:
                record_prompt_cache_miss("deterministic")
                return None

            cached.hit_count += 1
            cached.last_accessed_at = datetime.now()
            await db_session.commit()
            record_prompt_cache_hit("deterministic")

            return {
                "text": cached.response_text,
                "tokens_in": cached.tokens_in,
                "tokens_out": cached.tokens_out,
                "latency_ms": cached.latency_ms,
                "cache_hit": True,
            }

    async def _store_cached_response(self, agent: DebateAgent, prompt: str, response: dict[str, Any]) -> None:
        cache_key, prompt_hash = self._build_prompt_cache_key(agent, prompt)
        async with AsyncSessionLocal() as db_session:
            existing = await db_session.scalar(
                select(PromptResponseCache).where(PromptResponseCache.cache_key == cache_key)
            )
            if existing:
                existing.response_text = response["text"]
                existing.tokens_in = response["tokens_in"]
                existing.tokens_out = response["tokens_out"]
                existing.latency_ms = response["latency_ms"]
                existing.last_accessed_at = datetime.now()
            else:
                db_session.add(
                    PromptResponseCache(
                        cache_key=cache_key,
                        engine=agent.engine,
                        model=agent.model,
                        node=agent.node,
                        temperature=agent.temperature,
                        max_tokens=agent.max_tokens,
                        prompt_hash=prompt_hash,
                        response_text=response["text"],
                        tokens_in=response["tokens_in"],
                        tokens_out=response["tokens_out"],
                        latency_ms=response["latency_ms"],
                        hit_count=0,
                        last_accessed_at=datetime.now(),
                    )
                )
            await db_session.commit()

    async def create_debate(
        self,
        topic: str,
        agents_config: list[DebateAgent],
        on_turn_start: Callable[[DebateTurn], None] | None = None,
        on_turn_complete: Callable[[DebateTurn], None] | None = None,
        on_model_load: Callable[[str, str], None] | None = None,
        on_model_unload: Callable[[str, str], None] | None = None,
        mode: str = "standard",
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
            mode=mode,
        )

    async def create_debate_with_id(
        self,
        session_id: str,
        topic: str,
        agents_config: list[DebateAgent],
        on_turn_start: Callable[[DebateTurn], None] | None = None,
        on_turn_complete: Callable[[DebateTurn], None] | None = None,
        on_model_load: Callable[[str, str], None] | None = None,
        on_model_unload: Callable[[str, str], None] | None = None,
        mode: str = "standard",
    ) -> DebateSession:
        """Crea y ejecuta un debate secuencial con un ID proporcionado"""

        session = DebateSession(id=session_id, topic=topic, status="running")
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
                    total_turns=len(agents_config),
                )
                db_session.add(db_debate)
                await db_session.commit()
                logger.info("sequential_debate.db_created", session_id=session_id)
        except Exception as e:
            logger.error("sequential_debate.db_error", session_id=session_id, error=str(e))

        logger.info(
            "sequential_debate.created",
            session_id=session_id,
            topic=topic,
            num_agents=len(agents_config),
        )

        # Lanzar búsqueda web al inicio del debate (no bloqueante)
        if settings.WEB_AGENT_ENABLED:
            try:
                logger.info("sequential_debate.web_search_starting", session_id=session_id)
                web_search = get_web_search_service()
                web_ctx = await web_search.search_for_debate(topic, timeout_per_site=90)
                session.web_context = web_ctx.to_dict()
                logger.info(
                    "sequential_debate.web_search_completed",
                    session_id=session_id,
                    sites=len(web_ctx.searches),
                )

                # Guardar web_context en la base de datos
                try:
                    async with AsyncSessionLocal() as db_session:
                        db_debate = await db_session.get(SequentialDebate, session_id)
                        if db_debate:
                            db_debate.web_context = web_ctx.to_dict()
                            await db_session.commit()
                except Exception as e:
                    logger.warning("sequential_debate.web_context_db_failed", error=str(e))
            except Exception as e:
                logger.warning("sequential_debate.web_search_failed", error=str(e))

        try:
            # Variable para rastrear el modelo anterior y liberarlo de RAM
            previous_model = None

            for idx, agent_config in enumerate(agents_config, 1):
                next_preload_model = self._find_next_preload_model(agents_config, idx - 1)
                if next_preload_model:
                    self.local_manager.schedule_ollama_preload(next_preload_model)

                # Liberar modelo anterior de la RAM del worker antes de cargar el nuevo
                if previous_model and agent_config.node == "LOCAL" and agent_config.engine == "ollama":
                    try:
                        logger.info(
                            "sequential_debate.unloading_previous_model",
                            session_id=session_id,
                            previous_model=previous_model,
                            current_agent=agent_config.name,
                        )
                        # Obtener el cliente Ollama del engine manager
                        ollama_client = self.local_manager.engines.get(EngineType.OLLAMA)
                        if ollama_client:
                            await ollama_client.unload_model(previous_model)
                    except Exception as e:
                        logger.warning(
                            "sequential_debate.unload_failed",
                            session_id=session_id,
                            previous_model=previous_model,
                            error=str(e),
                        )

                turn = DebateTurn(
                    turn_number=idx,
                    agent=agent_config,
                    prompt_sent="",
                    started_at=datetime.now(),
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
                logger.info(
                    "sequential_debate.turn_start",
                    session_id=session_id,
                    turn=idx,
                    agent=agent_config.name,
                    model=agent_config.model,
                )

                try:
                    if agent_config.node == "LOCAL":
                        response = await self._run_local_agent(agent_config, full_prompt, on_model_unload)
                    else:  # CLOUD
                        response = await self._run_cloud_agent(agent_config, full_prompt)

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
                        intervention_type = detect_intervention_type(turn.response_received, agent_config.role.value)

                        # Usar task_manager para mejor manejo de errores
                        await submit_reputation_update(
                            reputation_service=reputation_service,
                            model=agent_config.model,
                            provider=agent_config.provider,
                            role=agent_config.role.value,
                            tokens_out=turn.tokens_out,
                            latency_ms=turn.latency_ms,
                            success=True,
                            intervention_type=intervention_type,
                        )
                    except Exception as e:
                        # Log error pero no propagar - reputación no es crítica
                        logger.debug(
                            "reputation.update_failed",
                            error=str(e),
                            model=agent_config.model,
                        )

                    logger.info(
                        "sequential_debate.turn_complete",
                        session_id=session_id,
                        turn=idx,
                        tokens_out=turn.tokens_out,
                        latency_ms=turn.latency_ms,
                    )

                except Exception as e:
                    logger.warning(
                        "sequential_debate.cloud_failed_fallback",
                        session_id=session_id,
                        turn=idx,
                        agent=agent_config.name,
                        error=str(e),
                    )

                    # Fallback: Usar modelo local si cloud falla
                    if agent_config.node == "CLOUD":
                        logger.info(
                            "sequential_debate.using_fallback",
                            session_id=session_id,
                            turn=idx,
                            fallback_model="llama3:8b",
                        )

                        # Crear agente fallback local - asegurar role tiene valor
                        fallback_role = agent_config.role if hasattr(agent_config, "role") else AgentRole.REFINER
                        logger.info(
                            "sequential_debate.fallback_creating",
                            session_id=session_id,
                            turn=idx,
                            fallback_role=fallback_role.value
                            if hasattr(fallback_role, "value")
                            else str(fallback_role),
                        )
                        fallback_agent = DebateAgent(
                            id=f"{agent_config.id}_fallback",
                            name=f"{agent_config.name} (Fallback Local)",
                            role=fallback_role,
                            node="LOCAL",
                            engine="ollama",
                            model="llama3:8b",
                            provider="meta",
                            system_prompt=agent_config.system_prompt
                            + "\n\n[Nota: Actúas como respaldo local debido a indisponibilidad del servicio cloud]",
                            temperature=agent_config.temperature,
                            max_tokens=agent_config.max_tokens,
                        )

                        try:
                            response = await self._run_local_agent(fallback_agent, full_prompt, on_model_unload)
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
                                            completed_at=turn.completed_at,
                                        )
                                    )
                                    await db_session.commit()
                                    logger.info(
                                        "sequential_debate.fallback_db_updated",
                                        session_id=session_id,
                                        turn=idx,
                                    )
                            except Exception as db_update_error:
                                logger.error(
                                    "sequential_debate.fallback_db_update_failed",
                                    session_id=session_id,
                                    turn=idx,
                                    error=str(db_update_error),
                                )

                            logger.info(
                                "sequential_debate.fallback_success",
                                session_id=session_id,
                                turn=idx,
                                tokens_out=turn.tokens_out,
                            )

                        except Exception as fallback_error:
                            turn.status = "failed"
                            turn.response_received = f"[ERROR Cloud: {e!s}]\n[ERROR Fallback: {fallback_error!s}]"
                            logger.error(
                                "sequential_debate.fallback_failed",
                                session_id=session_id,
                                turn=idx,
                                error=str(fallback_error),
                            )
                    else:
                        logger.info(
                            "sequential_debate.local_agent_failed_trying_fallback",
                            session_id=session_id,
                            turn=idx,
                            failed_model=agent_config.model,
                        )
                        fallback_role = agent_config.role if hasattr(agent_config, "role") else AgentRole.REFINER
                        fallback_agent = DebateAgent(
                            id=f"{agent_config.id}_fallback",
                            name=f"{agent_config.name} (Fallback)",
                            role=fallback_role,
                            node="LOCAL",
                            engine="ollama",
                            model="llama3:8b",
                            provider="meta",
                            system_prompt=agent_config.system_prompt
                            + "\n\n[Nota: Respaldo local - el modelo original falló al generar]",
                            temperature=agent_config.temperature,
                            max_tokens=agent_config.max_tokens,
                        )
                        try:
                            response = await self._run_local_agent(fallback_agent, full_prompt, on_model_unload)
                            turn.response_received = response["text"]
                            turn.tokens_in = response["tokens_in"]
                            turn.tokens_out = response["tokens_out"]
                            turn.latency_ms = response["latency_ms"]
                            turn.status = "completed (fallback)"
                            turn.agent = fallback_agent
                            turn.completed_at = datetime.now()

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
                                            completed_at=turn.completed_at,
                                        )
                                    )
                                    await db_session.commit()
                            except Exception as db_update_error:
                                logger.error(
                                    "sequential_debate.fallback_db_update_failed",
                                    session_id=session_id,
                                    turn=idx,
                                    error=str(db_update_error),
                                )

                            logger.info(
                                "sequential_debate.local_fallback_success",
                                session_id=session_id,
                                turn=idx,
                                tokens_out=turn.tokens_out,
                            )
                        except Exception as fallback_error:
                            turn.status = "failed"
                            turn.response_received = f"[ERROR Local: {e!s}]\n[ERROR Fallback: {fallback_error!s}]"
                            logger.error(
                                "sequential_debate.local_fallback_failed",
                                session_id=session_id,
                                turn=idx,
                                error=str(fallback_error),
                            )

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
                                max_rounds=len(agents_config),
                            )

                            logger.info(
                                "sequential_debate.convergence_evaluated",
                                session_id=session_id,
                                round=idx,
                                should_stop=convergence_result.should_stop,
                                consensus_level=convergence_result.consensus_level,
                            )

                            if convergence_result.should_stop:
                                logger.info(
                                    "sequential_debate.early_stop",
                                    session_id=session_id,
                                    round=idx,
                                    reason=convergence_result.consensus_level,
                                )
                                session.convergence_level = convergence_result.consensus_level
                                session.consensus_score = convergence_result.similarity_score
                                logger.info(
                                    "sequential_debate.breaking_loop",
                                    session_id=session_id,
                                )
                                break
                    except Exception as e:
                        logger.error(
                            "sequential_debate.convergence_exception",
                            session_id=session_id,
                            error=str(e),
                            error_type=type(e).__name__,
                        )

                # Persistir turno en base de datos
                try:
                    async with AsyncSessionLocal() as db_session:
                        # Asegurar que agent_role siempre tenga valor
                        agent_role_value = (
                            turn.agent.role.value if hasattr(turn.agent.role, "value") else str(turn.agent.role)
                        )
                        logger.debug(
                            "sequential_debate.saving_turn_db",
                            session_id=session_id,
                            turn=turn.turn_number,
                            agent_role=agent_role_value,
                        )

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
                            completed_at=turn.completed_at,
                        )
                        db_session.add(db_turn)
                        await db_session.commit()
                        logger.debug(
                            "sequential_debate.turn_saved_db",
                            session_id=session_id,
                            turn=turn.turn_number,
                        )
                except Exception as e:
                    logger.error(
                        "sequential_debate.turn_db_error",
                        session_id=session_id,
                        turn=turn.turn_number,
                        error=str(e),
                    )

                # Pequeña pausa entre turnos
                await asyncio.sleep(1)

            logger.info(
                "sequential_debate.for_loop_finished",
                session_id=session_id,
                iterations_completed=idx,
            )

            # Ejecutar Tribunal de Magistrados (si hay suficientes turnos completados)
            tribunal_result = None
            completed_turns = [t for t in session.turns if t.status == "completed"]

            if len(completed_turns) >= 2:
                logger.info(
                    "sequential_debate.tribunal_call_start",
                    session_id=session_id,
                    completed_turns=len(completed_turns),
                )
                try:
                    async with AsyncSessionLocal() as db_session:
                        tribunal_result = await self._run_tribunal(session, db_session)
                        logger.info(
                            "sequential_debate.tribunal_call_completed",
                            session_id=session_id,
                        )
                        if tribunal_result:
                            session.tribunal_verdict = tribunal_result
                            session.consensus_score = (
                                tribunal_result.get("evidence_score", 50)
                                + tribunal_result.get("risk_score", 50)
                                + tribunal_result.get("alignment_score", 50)
                            ) / 3
                            session.convergence_level = (
                                "CONSENSUS_REACHED" if tribunal_result.get("consensus_reached") else "PARTIAL_CONSENSUS"
                            )
                except Exception as e:
                    logger.error(
                        "sequential_debate.tribunal_failed",
                        session_id=session_id,
                        error=str(e),
                    )
            else:
                logger.warning(
                    "sequential_debate.tribunal_skipped",
                    session_id=session_id,
                    reason="insufficient_completed_turns",
                    completed=len(completed_turns),
                )

            # Generar veredicto final
            if tribunal_result and tribunal_result.get("verdict_text"):
                session.final_verdict = tribunal_result["verdict_text"]
            else:
                session.final_verdict = self._generate_verdict(session)

            # Generar reporte estructurado JSON (v2.1)
            try:
                session.structured_report = await self._generate_structured_report(session)
                logger.info(
                    "sequential_debate.structured_report_generated",
                    session_id=session_id,
                )
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
                        logger.info(
                            "sequential_debate.db_finalized",
                            session_id=session_id,
                            transcript_path=transcript_path,
                        )

                        # Trigger del Data Warehouse
                        try:
                            warehouse_mgr = _get_warehouse_manager()
                            await warehouse_mgr.process_sequential_debate(session_id)
                        except Exception as e:
                            logger.warning(
                                "sequential_debate.warehouse_failed",
                                session_id=session_id,
                                error=str(e),
                            )

                        # Generar informe HTML profesional
                        try:
                            from sqlalchemy import select

                            from backend.engine.report_generator import save_pdf_report, save_report

                            # Preparar datos de turnos desde la DB

                            turns_result = await db_session.execute(
                                select(SequentialDebateTurn)
                                .where(SequentialDebateTurn.debate_id == session_id)
                                .order_by(SequentialDebateTurn.turn_number)
                            )
                            db_turns = turns_result.scalars().all()
                            turns_data = [
                                {
                                    "turn_number": t.turn_number,
                                    "agent_name": t.agent_name,
                                    "agent_role": t.agent_role,
                                    "model": t.model,
                                    "provider": t.provider,
                                    "prompt_sent": t.prompt_sent,
                                    "response_received": t.response_received,
                                    "tokens_in": t.tokens_in,
                                    "tokens_out": t.tokens_out,
                                    "latency_ms": t.latency_ms,
                                    "quality_score": getattr(t, "quality_score", None),
                                }
                                for t in db_turns
                            ]

                            report_data = {
                                "id": session_id,
                                "topic": db_debate.topic,
                                "status": db_debate.status,
                                "total_tokens_in": db_debate.total_tokens_in,
                                "total_tokens_out": db_debate.total_tokens_out,
                                "total_latency_ms": db_debate.total_latency_ms,
                                "created_at": str(db_debate.created_at),
                                "completed_at": str(db_debate.completed_at),
                                "web_context": db_debate.web_context,
                            }

                            # HTML report
                            html_path = save_report(
                                debate_id=session_id,
                                debate_data=report_data,
                                turns=turns_data,
                                verdict=db_debate.final_verdict or "",
                                structured_report=db_debate.structured_report,
                            )
                            logger.info(
                                "sequential_debate.html_report_generated",
                                session_id=session_id,
                                report_path=html_path,
                            )

                            # PDF report
                            pdf_path = save_pdf_report(
                                debate_id=session_id,
                                debate_data=report_data,
                                turns=turns_data,
                                verdict=db_debate.final_verdict or "",
                                structured_report=db_debate.structured_report,
                            )
                            logger.info(
                                "sequential_debate.pdf_report_generated",
                                session_id=session_id,
                                report_path=pdf_path,
                            )
                        except Exception as e:
                            logger.warning(
                                "sequential_debate.report_failed",
                                session_id=session_id,
                                error=str(e),
                            )
            except Exception as e:
                logger.error(
                    "sequential_debate.final_db_error",
                    session_id=session_id,
                    error=str(e),
                )

            logger.info(
                "sequential_debate.completed",
                session_id=session_id,
                total_turns=len(session.turns),
                total_tokens=sum(t.tokens_out for t in session.turns),
                transcript_path=transcript_path,
            )
            record_debate_completed(
                total_tokens_out=sum(t.tokens_out for t in session.turns),
                total_latency_ms=sum(t.latency_ms for t in session.turns),
                mode=mode,
            )

            # Sincronización asíncrona con Supabase (usando HybridMemoryV2)
            try:
                from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2

                hybrid_mem = get_hybrid_memory_v2()
                # Usar task_manager para mejor manejo de errores
                await task_manager.submit(
                    lambda: hybrid_mem.enqueue_sync(session, session_id, mode),
                    context="hybrid_memory_sync",
                    config=TaskConfig(max_retries=2, retry_delay_seconds=1.0, log_success=False),
                )
            except Exception as e:
                logger.debug("hybrid_memory.sync_failed", error=str(e), session_id=session_id)
                # Fallback: usar método legacy si existe
                try:
                    from backend.engine.task_manager import submit_supabase_sync

                    await submit_supabase_sync(
                        supabase_service=_get_supabase_service(),
                        debate_data={
                            "id": session_id,
                            "session": session,
                            "mode": mode,
                        },
                    )
                except Exception as e:
                    logger.debug("supabase.sync_failed", error=str(e), session_id=session_id)

        except Exception as e:
            session.status = "failed"
            logger.error(
                "sequential_debate.outer_exception",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Actualizar estado en BD
            try:
                async with AsyncSessionLocal() as db_session:
                    db_debate = await db_session.get(SequentialDebate, session_id)
                    if db_debate:
                        db_debate.status = "failed"
                        await db_session.commit()
            except Exception:
                pass
            logger.error("sequential_debate.failed", session_id=session_id, error=str(e))

        return session

    async def _run_local_agent(
        self,
        agent: DebateAgent,
        prompt: str,
        on_model_unload: Callable[[str, str], None] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta agente local con Ollama"""
        cached_response = await self._get_cached_response(agent, prompt)
        if cached_response:
            return cached_response

        start_time = datetime.now()
        engine_type = EngineType(agent.engine)

        timeout_seconds = settings.get_model_timeout(agent.model, agent.engine)

        logger.info(
            "sequential_debate.local_agent_start",
            model=agent.model,
            engine=agent.engine,
            timeout_seconds=timeout_seconds,
        )

        response_parts = []
        tokens_out = 0

        async def _generate_tokens():
            nonlocal tokens_out
            async for token in self.local_manager.generate(
                engine_type=engine_type,
                model=agent.model,
                prompt=prompt,
                system=None,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
                stream=True,
            ):
                response_parts.append(token)
                tokens_out += 1

        try:
            await asyncio.wait_for(_generate_tokens(), timeout=timeout_seconds)
        except TimeoutError:
            logger.error(
                "sequential_debate.local_agent_timeout",
                model=agent.model,
                timeout_seconds=timeout_seconds,
                tokens_generated=tokens_out,
            )
            raise TimeoutError(
                f"Model '{agent.model}' timed out after {timeout_seconds}s "
                f"({tokens_out} tokens generated). "
                f"Increase MODEL_TIMEOUTS in .env or use a smaller model."
            )

        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        full_text = "".join(response_parts)
        if not full_text.strip() or tokens_out == 0:
            raise RuntimeError(
                f"Local agent {agent.model} ({agent.engine}) returned empty response "
                f"(model failed to generate, possibly unloaded or GPU OOM)"
            )

        if on_model_unload:
            on_model_unload(agent.model, agent.provider)

        result = {
            "text": full_text,
            "tokens_in": len(prompt.split()),
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "cache_hit": False,
        }
        await self._store_cached_response(agent, prompt, result)
        return result

    async def _run_cloud_agent(self, agent: DebateAgent, prompt: str) -> dict[str, Any]:
        """
        Ejecuta agente cloud según su engine: groq, gemini, deepseek, openrouter.
        Hace fallback a OpenRouter si el engine específico no está disponible.
        """
        start_time = datetime.now()
        messages = [{"role": "user", "content": prompt}]
        response_parts: list[str] = []
        tokens_out = 0

        engine = agent.engine.lower()
        timeout_seconds = settings.get_model_timeout(agent.model, engine)

        async def _stream(client_generator):
            nonlocal tokens_out
            async for token in client_generator:
                response_parts.append(token)
                tokens_out += 1

        async def _run_cloud_request():
            if engine == "groq" and settings.GROQ_API_KEY:
                from backend.adapters.groq import GroqClient

                client = GroqClient()
                await _stream(
                    client.chat_completion(
                        model=agent.model,
                        messages=messages,
                        temperature=agent.temperature,
                        max_tokens=agent.max_tokens,
                        stream=True,
                    )
                )

            elif engine == "gemini" and settings.GEMINI_API_KEY:
                from backend.adapters.gemini import GeminiClient

                client = GeminiClient()
                await _stream(
                    client.chat_completion(
                        model=agent.model,
                        messages=messages,
                        temperature=agent.temperature,
                        max_tokens=agent.max_tokens,
                        stream=True,
                    )
                )

            elif engine == "deepseek" and settings.DEEPSEEK_API_KEY:
                from backend.adapters.deepseek import DeepSeekClient

                client = DeepSeekClient()
                await _stream(
                    client.chat_completion(
                        model=agent.model,
                        messages=messages,
                        temperature=agent.temperature,
                        max_tokens=agent.max_tokens,
                        stream=True,
                    )
                )

            elif self.openrouter:
                await _stream(
                    self.openrouter.chat_completion(
                        model=agent.model,
                        messages=messages,
                        temperature=agent.temperature,
                        max_tokens=agent.max_tokens,
                        stream=True,
                    )
                )

            else:
                raise RuntimeError(
                    f"No cloud client available for engine='{agent.engine}'. "
                    "Configure at least one API key (GROQ, GEMINI, DEEPSEEK, OPENROUTER)."
                )

        try:
            await asyncio.wait_for(_run_cloud_request(), timeout=timeout_seconds)
        except TimeoutError:
            logger.error(
                "sequential_debate.cloud_agent_timeout",
                model=agent.model,
                engine=engine,
                timeout_seconds=timeout_seconds,
                tokens_generated=tokens_out,
            )
            raise TimeoutError(
                f"Cloud model '{agent.model}' ({engine}) timed out after {timeout_seconds}s "
                f"({tokens_out} tokens generated). "
                f"Increase MODEL_TIMEOUTS in .env or use a faster model."
            )

        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        response_text = "".join(response_parts)

        if not response_text.strip() or tokens_out == 0:
            raise RuntimeError(
                f"Cloud agent {agent.model} ({engine}) returned empty response (quota exceeded or model unavailable)"
            )

        return {
            "text": response_text,
            "tokens_in": len(prompt.split()),  # Aproximación
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
        }

    def _generate_verdict(self, session: DebateSession) -> str:
        """Genera un veredicto final del debate"""

        verdict_lines = [
            "# VEREDICTO DEL SYNAPSE COUNCIL",
            f"## Tema: {session.topic}",
            "",
            "### Participantes",
        ]

        for turn in session.turns:
            verdict_lines.append(
                f"- **{turn.agent.name}** ({turn.agent.role.value}): {turn.agent.model} ({turn.agent.provider})"
            )

        verdict_lines.extend(["", "### Resumen del Debate", ""])

        # Extraer puntos clave de cada turno (primeras 200 chars)
        for turn in session.turns:
            if turn.status == "completed":
                preview = turn.response_received[:200].replace("\n", " ")
                verdict_lines.append(f"**{turn.agent.role.value.upper()}** ({turn.agent.provider}): {preview}...")

        verdict_lines.extend(
            [
                "",
                "---",
                "*Veredicto emitido por el Tribunal de Magistrados del Synapse Council v2.0*",
            ]
        )

        return "\n".join(verdict_lines)

    async def _run_tribunal(self, session: DebateSession, db_session: AsyncSession) -> dict[str, Any] | None:
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
                    f"### {turn.agent.name} ({turn.agent.role.value})\n{turn.response_received}"
                )
            local_synthesis = "\n\n".join(local_synthesis_parts)

            # Para debate secuencial, cloud_synthesis es vacío (solo local)
            cloud_synthesis = ""

            # Preparar contexto web para el tribunal
            web_context_str = ""
            if session.web_context:
                from backend.engine.web_search_service import WebContext

                web_ctx = WebContext.from_dict(session.web_context)
                web_search = get_web_search_service()
                web_context_str = web_search.format_web_context_for_tribunal(web_ctx)

            # Llamar al Tribunal
            verdict = await self.tribunal.issue_verdict(
                session_id=session.id,
                round_id=session.id,  # Usar session_id como round_id
                round_number=1,
                query=session.topic,
                local_synthesis=local_synthesis,
                cloud_synthesis=cloud_synthesis,
                db_session=db_session,
                on_event=None,  # Sin callbacks por ahora
                web_context=web_context_str if web_context_str else None,
            )

            logger.info(
                "sequential_debate.tribunal_verdict_received",
                session_id=session.id,
                has_verdict_text=bool(verdict.verdict_text if verdict else False),
                consensus_reached=verdict.consensus_reached if verdict else None,
            )

            # Retornar dict serializable
            return {
                "verdict_text": verdict.verdict_text,
                "consensus_reached": verdict.consensus_reached,
                "iterations_required": verdict.iterations_required,
                "evidence_score": verdict.evidence_score,
                "risk_score": verdict.risk_score,
                "alignment_score": verdict.alignment_score,
                "dissent_areas": verdict.dissent_areas,
            }

        except Exception as e:
            logger.error(
                "sequential_debate.tribunal_failed",
                session_id=session.id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def _generate_structured_report(self, session: DebateSession) -> dict[str, Any]:
        """
        Genera un informe estructurado JSON resumiendo el debate.
        Utiliza un modelo local rápido para la extracción.
        """
        logger.info("sequential_debate.generating_structured_report", session_id=session.id)

        history = []
        completed_turns = 0
        for t in session.turns:
            if t.status.startswith("completed"):
                completed_turns += 1
                history.append(f"Agente {t.agent.name}: {t.response_received[:500]}")

        return await self._generate_structured_report_from_history(
            session_id=session.id,
            topic=session.topic,
            history=history,
            total_turns=len(session.turns),
            completed_turns=completed_turns,
        )

    async def _generate_structured_report_from_history(
        self,
        session_id: str,
        topic: str,
        history: list[str],
        total_turns: int,
        completed_turns: int,
    ) -> dict[str, Any]:
        """Genera un informe estructurado a partir del historial textual del debate."""
        fallback_report = {
            "summary": f"Debate sobre {topic} con {total_turns} turnos.",
            "consensus_level": 50,
            "key_findings": [f"Turnos completados: {completed_turns}"],
            "risks_identified": [],
            "action_items": [],
            "generated_by": "fallback",
        }

        full_text = "\n\n".join(history)

        prompt = f"""Analiza el siguiente debate y genera un objeto JSON con el resumen ejecutivo.
TEMA: {topic}

DEBATE:
{full_text}

INSTRUCCIONES CRÍTICAS:
1. RESPONDE ÚNICAMENTE CON UN OBJETO JSON VÁLIDO
2. NO incluyas texto antes o después del JSON
3. NO uses bloques de código markdown (```json o ```)
4. Usa comillas dobles para todas las claves y strings
5. NO uses comas trailing (último elemento sin coma)
6. El JSON debe tener esta estructura exacta:
{{
  "summary": "Resumen de 2 párrafos",
  "consensus_level": 0-100,
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
                model="llama3:8b",
                prompt=prompt,
                temperature=0.1,
                max_tokens=800,
            ):
                response_text += token

            # Extraer JSON de la respuesta - manejar múltiples formatos
            report_data = self._extract_json_from_llm_response(response_text)
            if report_data:
                report_data["generated_by"] = "llama3:8b"
                logger.info(
                    "sequential_debate.structured_report.parsed_successfully",
                    session_id=session_id,
                )
                return report_data

            # Si falla el parsing, intentar reparar con enfoque más agresivo
            logger.warning(
                "sequential_debate.structured_report.parsing_failed_retrying",
                session_id=session_id,
                response_preview=response_text[:300],
            )

            # Intentar extraer cualquier JSON válido del texto
            import re

            # Buscar el bloque JSON más grande posible
            json_candidates = re.findall(r"\{[\s\S]*\}", response_text)
            for candidate in sorted(json_candidates, key=len, reverse=True):
                # Limpiar y reparar
                cleaned = candidate.strip()
                cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)  # Comas trailing
                cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)  # Caracteres de control
                try:
                    report_data = json.loads(cleaned)
                    report_data["generated_by"] = "llama3:8b_repaired"
                    logger.info(
                        "sequential_debate.structured_report.repaired_successfully",
                        session_id=session_id,
                    )
                    return report_data
                except json.JSONDecodeError:
                    continue

            logger.warning(
                "sequential_debate.structured_report.no_json_found",
                session_id=session_id,
                response_preview=response_text[:200],
            )
            return fallback_report
        except Exception as e:
            logger.error(
                "sequential_debate.structured_report.exception",
                session_id=session_id,
                error=str(e),
            )
            return fallback_report

    def _extract_json_from_llm_response(self, text: str) -> dict | None:
        """
        Extrae JSON de respuestas LLM con múltiples estrategias de recuperación.

        Maneja:
        - JSON puro
        - JSON dentro de ```json ... ``` o ``` ... ```
        - JSON precedido/sucedido por texto explicativo
        - Comas trailing, comillas simples, caracteres de escape
        """
        import re

        if not text or not text.strip():
            return None

        # Pre-limpieza: quitar BOM, caracteres invisibles
        text = text.strip().lstrip("\ufeff").strip()

        def try_parse(json_str: str) -> dict | None:
            """Intenta parsear JSON con reparaciones comunes"""
            if not json_str or not json_str.strip():
                return None

            cleaned = json_str.strip()

            # Reparación 1: Comas trailing antes de } o ]
            cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

            # Reparación 2: Comillas simples por dobles (solo si no hay dobles dentro)
            if "'" in cleaned and '"' not in cleaned:
                cleaned = cleaned.replace("'", '"')

            # Reparación 3: Quitar caracteres de control no válidos
            cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)

            # Reparación 4: Asegurar que empieza con { y termina con }
            brace_start = cleaned.find("{")
            brace_end = cleaned.rfind("}")
            if brace_start != -1 and brace_end > brace_start:
                cleaned = cleaned[brace_start : brace_end + 1]

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                logger.debug("sequential_debate.json_parse_failed", error=str(e), snippet=cleaned[:200])
                return None

        # Estrategia 1: Bloque ```json ... ``` (más específico primero)
        match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if match:
            result = try_parse(match.group(1))
            if result:
                return result

        # Estrategia 2: Bloque ``` ... ``` genérico
        match = re.search(r"```\s*([\s\S]*?)\s*```", text)
        if match:
            result = try_parse(match.group(1))
            if result:
                return result

        # Estrategia 3: JSON puro (empieza con { y termina con })
        if text.startswith("{") and text.endswith("}"):
            result = try_parse(text)
            if result:
                return result

        # Estrategia 4: Encontrar el primer { ... } balanceado
        brace_start = text.find("{")
        if brace_start != -1:
            depth = 0
            in_string = False
            escape_next = False
            for i in range(brace_start, len(text)):
                ch = text[i]
                if escape_next:
                    escape_next = False
                    continue
                if ch == "\\":
                    escape_next = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if not in_string:
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            result = try_parse(text[brace_start : i + 1])
                            if result:
                                return result
                            break

        # Estrategia 5: Buscar cualquier objeto JSON en el texto (último recurso)
        matches = re.findall(r"\{[^{}]*\}", text)
        for m in reversed(matches):  # Intentar desde el más grande
            result = try_parse(m)
            if result:
                return result

        return None

    async def generate_structured_report_for_debate(self, session_id: str) -> dict[str, Any] | None:
        """
        Regenera y persiste el structured_report para debates completados que no lo tengan.
        Sirve como backfill para reportes históricos.
        """
        debate = await self.get_debate_from_db(session_id)
        if not debate or debate.get("status") != "completed":
            return None

        completed_turns = []
        for turn in debate.get("turns", []):
            if str(turn.get("status", "")).startswith("completed"):
                response_text = turn.get("response_received") or turn.get("response_preview") or ""
                if response_text:
                    completed_turns.append(f"Agente {turn.get('agent_name', 'unknown')}: {response_text[:500]}")

        report = await self._generate_structured_report_from_history(
            session_id=session_id,
            topic=debate.get("topic", ""),
            history=completed_turns,
            total_turns=len(debate.get("turns", [])),
            completed_turns=len(completed_turns),
        )

        try:
            async with AsyncSessionLocal() as db_session:
                db_debate = await db_session.get(SequentialDebate, session_id)
                if db_debate:
                    db_debate.structured_report = report
                    await db_session.commit()
                    logger.info(
                        "sequential_debate.structured_report_backfilled",
                        session_id=session_id,
                    )
        except Exception as e:
            logger.error(
                "sequential_debate.structured_report_backfill_failed",
                session_id=session_id,
                error=str(e),
            )

        return report

    async def _persist_reductio_absurdum_proof(
        self,
        debate_id: str,
        iteration_number: int,
        complacency_scan: ComplacencyScan,
        proof,
    ) -> None:
        """Persiste una prueba de reducción al absurdo junto a su contexto de complacencia."""
        async with AsyncSessionLocal() as db_session:
            db_session.add(
                ReductioAbsurdumProof(
                    debate_id=debate_id,
                    iteration_number=iteration_number,
                    proposition=proof.proposition,
                    extreme_case=proof.extreme_case,
                    contradiction=proof.contradiction,
                    is_valid=proof.is_valid,
                    confidence_score=proof.confidence_score,
                    questioning_agent=proof.questioning_agent,
                    challenged_agent=proof.challenged_agent,
                    consensus_areas=complacency_scan.consensus_areas,
                    weak_assumptions=complacency_scan.weak_assumptions,
                    unquestioned_premises=complacency_scan.unquestioned_premises,
                    overall_complacency_risk=complacency_scan.overall_complacency_risk,
                    recommendations=complacency_scan.recommendations,
                )
            )
            await db_session.commit()

    def _on_absurdum_proof_created(self, proof: "AbsurdumProof") -> None:
        """Callback sincrono para persistir pruebas de reduccion al absurdo"""
        # Este metodo se llama desde el engine de reductio cuando se genera una prueba
        # La persistencia real ya se hace via _persist_reductio_absurdum_proof
        # Este callback es para logging y tracking adicional
        logger.info(
            "sequential_debate.absurdum_proof_callback",
            proof_proposition=proof.proposition[:80],
            contradiction_found=bool(proof.contradiction),
            is_valid=proof.is_valid,
        )

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
            f"- **Tiempo Total:** {sum(t.latency_ms for t in session.turns) / 1000:.1f}s",
            "",
            "=" * 80,
            "",
        ]

        # Detalle de cada turno
        for turn in session.turns:
            lines.extend(
                [
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
                    "",
                ]
            )

        # Veredicto final
        if session.final_verdict:
            lines.extend(["", session.final_verdict, ""])

        # Guardar archivo
        content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(
            "sequential_debate.transcript_saved",
            session_id=session.id,
            filepath=filepath,
            size_bytes=len(content),
        )

        return filepath

    async def get_debate_from_db(self, session_id: str) -> dict[str, Any] | None:
        """Recupera un debate completo de la base de datos"""
        try:
            async with AsyncSessionLocal() as db_session:
                from sqlalchemy import select

                # Obtener debate
                result = await db_session.execute(select(SequentialDebate).where(SequentialDebate.id == session_id))
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
                    "structured_report": debate.structured_report,
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
                            "response_preview": t.response_received[:200] + "..."
                            if len(t.response_received) > 200
                            else t.response_received,
                            "response_received": t.response_received,
                            "tokens_in": t.tokens_in,
                            "tokens_out": t.tokens_out,
                            "latency_ms": t.latency_ms,
                            "status": t.status,
                        }
                        for t in turns
                    ],
                }
        except Exception as e:
            logger.error("sequential_debate.db_read_error", session_id=session_id, error=str(e))
            return None

    async def list_debates_from_db(self, limit: int = 50) -> list[dict[str, Any]]:
        """Lista debates históricos de la base de datos"""
        try:
            async with AsyncSessionLocal() as db_session:
                from sqlalchemy import desc, select

                result = await db_session.execute(
                    select(SequentialDebate).order_by(desc(SequentialDebate.created_at)).limit(limit)
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
                        "completed_at": d.completed_at,
                    }
                    for d in debates
                ]
        except Exception as e:
            logger.error("sequential_debate.db_list_error", error=str(e))
            return []

    async def _sync_to_supabase(self, session: DebateSession, session_id: str, mode: str = "local_only"):
        """Sincroniza debate con Supabase en background. No-op si Supabase no está configurado."""
        svc = _get_supabase_service()
        if not svc.enabled:
            return  # Supabase no configurado, salir silenciosamente

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
                        "completed_at": t.completed_at,
                    }
                    for t in session.turns
                ],
            }

            # Sincronizar
            result = await svc.sync_debate(debate_data)

            if result.get("synced"):
                logger.info(
                    "sequential_debate.supabase_synced",
                    session_id=session_id,
                    supabase_url=result.get("supabase_url"),
                )
            else:
                logger.warning(
                    "sequential_debate.supabase_failed",
                    session_id=session_id,
                    error=result.get("error"),
                )

        except Exception as e:
            logger.error(
                "sequential_debate.supabase_exception",
                session_id=session_id,
                error=str(e),
            )

    def get_session(self, session_id: str) -> DebateSession | None:
        """Obtiene una sesión de debate activa"""
        return self.active_sessions.get(session_id)

    def list_sessions(self) -> list[DebateSession]:
        """Lista todas las sesiones de debate"""
        return list(self.active_sessions.values())

    async def continue_debate(
        self,
        session_id: str,
        agents_config: list[DebateAgent] | None = None,
        max_additional_turns: int | None = None,
        continuation_prompt: str | None = None,
        on_turn_start: Callable[[DebateTurn], None] | None = None,
        on_turn_complete: Callable[[DebateTurn], None] | None = None,
        on_model_load: Callable[[str, str], None] | None = None,
        on_model_unload: Callable[[str, str], None] | None = None,
    ) -> DebateSession | None:
        """
        Continua un debate existente con nuevos turnos.

        Args:
            session_id: ID del debate a continuar
            agents_config: Agentes a usar (si None, reusa los del debate original)
            max_additional_turns: Maximo de turnos adicionales (si None, usa len(agents))
            continuation_prompt: Prompt adicional para guiar la continuacion
            callbacks: Mismos callbacks que create_debate_with_id

        Returns:
            DebateSession actualizada o None si no se encontro el debate
        """
        session = self.get_session(session_id)
        if not session:
            debate_data = await self.get_debate_from_db(session_id)
            if not debate_data:
                return None
            session = await self._reconstruct_session_from_db(debate_data)
            self.active_sessions[session_id] = session

        if session.status not in ("completed", "failed"):
            return None

        session.status = "running"
        session.completed_at = None
        session.final_verdict = None
        session.structured_report = None

        if not agents_config:
            agents_config = self._extract_agents_from_session(session)

        if not agents_config:
            agents_config = get_standard_debate_config(session.topic)

        num_turns = max_additional_turns or len(agents_config)
        agents_config = agents_config[:num_turns]

        start_turn_number = len(session.turns) + 1

        try:
            previous_model = None

            for idx, agent_config in enumerate(agents_config, start_turn_number):
                next_preload_model = self._find_next_preload_model(agents_config, idx - start_turn_number)
                if next_preload_model:
                    self.local_manager.schedule_ollama_preload(next_preload_model)

                if previous_model and agent_config.node == "LOCAL" and agent_config.engine == "ollama":
                    try:
                        ollama_client = self.local_manager.engines.get(EngineType.OLLAMA)
                        if ollama_client:
                            await ollama_client.unload_model(previous_model)
                    except Exception as e:
                        logger.warning(
                            "sequential_debate.unload_failed",
                            session_id=session_id,
                            previous_model=previous_model,
                            error=str(e),
                        )

                turn = DebateTurn(
                    turn_number=idx,
                    agent=agent_config,
                    prompt_sent="",
                    started_at=datetime.now(),
                )
                turn.status = "running"

                if on_model_load:
                    on_model_load(agent_config.model, agent_config.provider)

                context_prompt = session.build_context_prompt(agent_config)

                if continuation_prompt:
                    context_prompt += f"\n\n## Instruccion de Continuacion\n{continuation_prompt}"

                full_prompt = f"{context_prompt}\n\n{agent_config.system_prompt}"
                turn.prompt_sent = full_prompt

                if on_turn_start:
                    on_turn_start(turn)

                logger.info(
                    "sequential_debate.continuation_turn_start",
                    session_id=session_id,
                    turn=idx,
                    agent=agent_config.name,
                    model=agent_config.model,
                )

                try:
                    if agent_config.node == "LOCAL":
                        response = await self._run_local_agent(agent_config, full_prompt, on_model_unload)
                    else:
                        response = await self._run_cloud_agent(agent_config, full_prompt)

                    turn.response_received = response["text"]
                    turn.tokens_in = response["tokens_in"]
                    turn.tokens_out = response["tokens_out"]
                    turn.latency_ms = response["latency_ms"]

                    q_score, _ = evaluate_response(turn.response_received, agent_config.role.value)
                    turn.quality_score = q_score

                    turn.status = "completed"
                    turn.completed_at = datetime.now()

                    if agent_config.node == "LOCAL" and agent_config.engine == "ollama":
                        previous_model = agent_config.model

                    try:
                        intervention_type = detect_intervention_type(turn.response_received, agent_config.role.value)
                        await submit_reputation_update(
                            reputation_service=reputation_service,
                            model=agent_config.model,
                            provider=agent_config.provider,
                            role=agent_config.role.value,
                            tokens_out=turn.tokens_out,
                            latency_ms=turn.latency_ms,
                            success=True,
                            intervention_type=intervention_type,
                        )
                    except Exception as e:
                        logger.debug(
                            "reputation.update_failed",
                            error=str(e),
                            model=agent_config.model,
                        )

                    logger.info(
                        "sequential_debate.continuation_turn_complete",
                        session_id=session_id,
                        turn=idx,
                        tokens_out=turn.tokens_out,
                        latency_ms=turn.latency_ms,
                    )

                except Exception as e:
                    turn.status = "failed"
                    turn.response_received = f"[ERROR: {e!s}]"
                    logger.error(
                        "sequential_debate.continuation_turn_failed",
                        session_id=session_id,
                        turn=idx,
                        error=str(e),
                    )

                if on_turn_complete:
                    on_turn_complete(turn)

                session.turns.append(turn)

                try:
                    async with AsyncSessionLocal() as db_session:
                        agent_role_value = (
                            turn.agent.role.value if hasattr(turn.agent.role, "value") else str(turn.agent.role)
                        )
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
                            completed_at=turn.completed_at,
                        )
                        db_session.add(db_turn)
                        await db_session.commit()
                except Exception as e:
                    logger.error(
                        "sequential_debate.continuation_turn_db_error",
                        session_id=session_id,
                        turn=turn.turn_number,
                        error=str(e),
                    )

                await asyncio.sleep(1)

            completed_turns = [t for t in session.turns if t.status == "completed"]
            if len(completed_turns) >= 2:
                try:
                    async with AsyncSessionLocal() as db_session:
                        tribunal_result = await self._run_tribunal(session, db_session)
                        if tribunal_result:
                            session.tribunal_verdict = tribunal_result
                            session.consensus_score = (
                                tribunal_result.get("evidence_score", 50)
                                + tribunal_result.get("risk_score", 50)
                                + tribunal_result.get("alignment_score", 50)
                            ) / 3
                            session.convergence_level = (
                                "CONSENSUS_REACHED" if tribunal_result.get("consensus_reached") else "PARTIAL_CONSENSUS"
                            )
                except Exception as e:
                    logger.error(
                        "sequential_debate.continuation_tribunal_failed",
                        session_id=session_id,
                        error=str(e),
                    )

            if session.tribunal_verdict and session.tribunal_verdict.get("verdict_text"):
                session.final_verdict = session.tribunal_verdict["verdict_text"]
            else:
                session.final_verdict = self._generate_verdict(session)

            try:
                session.structured_report = await self._generate_structured_report(session)
            except Exception as e:
                logger.error("sequential_debate.continuation_report_failed", error=str(e))

            session.status = "completed"
            session.completed_at = datetime.now()

            transcript_path = await self._save_transcript(session)

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

                        try:
                            warehouse_mgr = _get_warehouse_manager()
                            await warehouse_mgr.process_sequential_debate(session_id)
                        except Exception as e:
                            logger.warning(
                                "sequential_debate.continuation_warehouse_failed",
                                session_id=session_id,
                                error=str(e),
                            )
            except Exception as e:
                logger.error(
                    "sequential_debate.continuation_final_db_error",
                    session_id=session_id,
                    error=str(e),
                )

            logger.info(
                "sequential_debate.continuation_completed",
                session_id=session_id,
                total_turns=len(session.turns),
                new_turns=len(agents_config),
            )

            return session

        except Exception as e:
            session.status = "failed"
            logger.error(
                "sequential_debate.continuation_exception",
                session_id=session_id,
                error=str(e),
            )
            try:
                async with AsyncSessionLocal() as db_session:
                    db_debate = await db_session.get(SequentialDebate, session_id)
                    if db_debate:
                        db_debate.status = "failed"
                        await db_session.commit()
            except Exception:
                pass
            return None

    async def _reconstruct_session_from_db(self, debate_data: dict[str, Any]) -> DebateSession:
        """Reconstruye una DebateSession desde datos de la base de datos"""
        session = DebateSession(
            id=debate_data["id"],
            topic=debate_data["topic"],
            status=debate_data["status"],
            created_at=debate_data["created_at"] if isinstance(debate_data["created_at"], datetime) else datetime.now(),
            completed_at=debate_data.get("completed_at"),
            final_verdict=debate_data.get("final_verdict"),
            structured_report=debate_data.get("structured_report"),
        )

        for turn_data in debate_data.get("turns", []):
            agent = DebateAgent(
                id=turn_data.get("agent_id", turn_data.get("agent_name", "unknown")),
                name=turn_data.get("agent_name", "Unknown Agent"),
                role=AgentRole(turn_data.get("agent_role", "analyst")),
                node=turn_data.get("node", "LOCAL"),
                engine=turn_data.get("engine", "ollama"),
                model=turn_data.get("model", "llama3:8b"),
                provider=turn_data.get("provider", "meta"),
                system_prompt="",
                temperature=0.7,
                max_tokens=500,
            )
            turn = DebateTurn(
                turn_number=turn_data["turn_number"],
                agent=agent,
                prompt_sent="",
                response_received=turn_data.get("response_received", turn_data.get("response_preview", "")),
                tokens_in=turn_data.get("tokens_in", 0),
                tokens_out=turn_data.get("tokens_out", 0),
                latency_ms=turn_data.get("latency_ms", 0),
                status=turn_data.get("status", "completed"),
                started_at=turn_data.get("started_at"),
                completed_at=turn_data.get("completed_at"),
            )
            session.turns.append(turn)

        return session

    def _extract_agents_from_session(self, session: DebateSession) -> list[DebateAgent]:
        """Extrae la configuracion de agentes desde los turnos existentes"""
        seen_ids = set()
        agents = []
        for turn in session.turns:
            if turn.agent.id not in seen_ids:
                seen_ids.add(turn.agent.id)
                agents.append(turn.agent)
        return agents

    async def pause_debate(
        self,
        session_id: str,
        reason: str | None = None,
    ) -> DebateSession | None:
        """
        Pausa un debate en ejecucion.

        Args:
            session_id: ID del debate a pausar
            reason: Motivo de la pausa (opcional)

        Returns:
            DebateSession pausada o None si no se encontro
        """
        session = self.get_session(session_id)
        if not session:
            debate_data = await self.get_debate_from_db(session_id)
            if not debate_data:
                return None
            if debate_data.get("status") != "running":
                return None
            session = await self._reconstruct_session_from_db(debate_data)
            self.active_sessions[session_id] = session

        if session.status != "running":
            return None

        session.status = "paused"
        session.paused_at = datetime.now()
        session.pause_reason = reason

        try:
            async with AsyncSessionLocal() as db_session:
                db_debate = await db_session.get(SequentialDebate, session_id)
                if db_debate:
                    db_debate.status = "paused"
                    db_debate.paused_at = session.paused_at
                    db_debate.pause_reason = reason
                    await db_session.commit()
                    logger.info(
                        "sequential_debate.paused_db_updated",
                        session_id=session_id,
                        reason=reason,
                    )
        except Exception as e:
            logger.error("sequential_debate.pause_db_error", session_id=session_id, error=str(e))

        logger.info(
            "sequential_debate.paused",
            session_id=session_id,
            turns_completed=len(session.turns),
            reason=reason,
        )

        return session

    async def resume_debate(
        self,
        session_id: str,
        on_turn_start: Callable[[DebateTurn], None] | None = None,
        on_turn_complete: Callable[[DebateTurn], None] | None = None,
        on_model_load: Callable[[str, str], None] | None = None,
        on_model_unload: Callable[[str, str], None] | None = None,
    ) -> DebateSession | None:
        """
        Reanuda un debate pausado desde donde se quedo.

        Args:
            session_id: ID del debate a reanudar
            callbacks: Mismos callbacks que create_debate_with_id

        Returns:
            DebateSession completada o None si no se encontro
        """
        session = self.get_session(session_id)
        if not session:
            debate_data = await self.get_debate_from_db(session_id)
            if not debate_data:
                return None
            if debate_data.get("status") != "paused":
                return None
            session = await self._reconstruct_session_from_db(debate_data)
            self.active_sessions[session_id] = session

        if session.status != "paused":
            return None

        session.status = "running"
        session.paused_at = None
        session.pause_reason = None

        try:
            async with AsyncSessionLocal() as db_session:
                db_debate = await db_session.get(SequentialDebate, session_id)
                if db_debate:
                    db_debate.status = "running"
                    db_debate.paused_at = None
                    db_debate.pause_reason = None
                    await db_session.commit()
        except Exception as e:
            logger.error("sequential_debate.resume_db_error", session_id=session_id, error=str(e))

        agents_config = self._extract_agents_from_session(session)
        if not agents_config:
            agents_config = get_standard_debate_config(session.topic)

        start_turn_number = len(session.turns) + 1

        logger.info(
            "sequential_debate.resumed",
            session_id=session_id,
            resume_from_turn=start_turn_number,
            total_agents=len(agents_config),
        )

        try:
            previous_model = None

            for idx, agent_config in enumerate(agents_config, start_turn_number):
                next_preload_model = self._find_next_preload_model(agents_config, idx - start_turn_number)
                if next_preload_model:
                    self.local_manager.schedule_ollama_preload(next_preload_model)

                if previous_model and agent_config.node == "LOCAL" and agent_config.engine == "ollama":
                    try:
                        ollama_client = self.local_manager.engines.get(EngineType.OLLAMA)
                        if ollama_client:
                            await ollama_client.unload_model(previous_model)
                    except Exception as e:
                        logger.warning(
                            "sequential_debate.unload_failed",
                            session_id=session_id,
                            previous_model=previous_model,
                            error=str(e),
                        )

                turn = DebateTurn(
                    turn_number=idx,
                    agent=agent_config,
                    prompt_sent="",
                    started_at=datetime.now(),
                )
                turn.status = "running"

                if on_model_load:
                    on_model_load(agent_config.model, agent_config.provider)

                context_prompt = session.build_context_prompt(agent_config)
                full_prompt = f"{context_prompt}\n\n{agent_config.system_prompt}"
                turn.prompt_sent = full_prompt

                if on_turn_start:
                    on_turn_start(turn)

                logger.info(
                    "sequential_debate.resume_turn_start",
                    session_id=session_id,
                    turn=idx,
                    agent=agent_config.name,
                    model=agent_config.model,
                )

                try:
                    if agent_config.node == "LOCAL":
                        response = await self._run_local_agent(agent_config, full_prompt, on_model_unload)
                    else:
                        response = await self._run_cloud_agent(agent_config, full_prompt)

                    turn.response_received = response["text"]
                    turn.tokens_in = response["tokens_in"]
                    turn.tokens_out = response["tokens_out"]
                    turn.latency_ms = response["latency_ms"]

                    q_score, _ = evaluate_response(turn.response_received, agent_config.role.value)
                    turn.quality_score = q_score

                    turn.status = "completed"
                    turn.completed_at = datetime.now()

                    if agent_config.node == "LOCAL" and agent_config.engine == "ollama":
                        previous_model = agent_config.model

                    try:
                        intervention_type = detect_intervention_type(turn.response_received, agent_config.role.value)
                        await submit_reputation_update(
                            reputation_service=reputation_service,
                            model=agent_config.model,
                            provider=agent_config.provider,
                            role=agent_config.role.value,
                            tokens_out=turn.tokens_out,
                            latency_ms=turn.latency_ms,
                            success=True,
                            intervention_type=intervention_type,
                        )
                    except Exception as e:
                        logger.debug(
                            "reputation.update_failed",
                            error=str(e),
                            model=agent_config.model,
                        )

                    logger.info(
                        "sequential_debate.resume_turn_complete",
                        session_id=session_id,
                        turn=idx,
                        tokens_out=turn.tokens_out,
                        latency_ms=turn.latency_ms,
                    )

                except Exception as e:
                    turn.status = "failed"
                    turn.response_received = f"[ERROR: {e!s}]"
                    logger.error(
                        "sequential_debate.resume_turn_failed",
                        session_id=session_id,
                        turn=idx,
                        error=str(e),
                    )

                if on_turn_complete:
                    on_turn_complete(turn)

                session.turns.append(turn)

                try:
                    async with AsyncSessionLocal() as db_session:
                        agent_role_value = (
                            turn.agent.role.value if hasattr(turn.agent.role, "value") else str(turn.agent.role)
                        )
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
                            completed_at=turn.completed_at,
                        )
                        db_session.add(db_turn)
                        await db_session.commit()
                except Exception as e:
                    logger.error(
                        "sequential_debate.resume_turn_db_error",
                        session_id=session_id,
                        turn=turn.turn_number,
                        error=str(e),
                    )

                await asyncio.sleep(1)

            completed_turns = [t for t in session.turns if t.status == "completed"]
            if len(completed_turns) >= 2:
                try:
                    async with AsyncSessionLocal() as db_session:
                        tribunal_result = await self._run_tribunal(session, db_session)
                        if tribunal_result:
                            session.tribunal_verdict = tribunal_result
                            session.consensus_score = (
                                tribunal_result.get("evidence_score", 50)
                                + tribunal_result.get("risk_score", 50)
                                + tribunal_result.get("alignment_score", 50)
                            ) / 3
                            session.convergence_level = (
                                "CONSENSUS_REACHED" if tribunal_result.get("consensus_reached") else "PARTIAL_CONSENSUS"
                            )
                except Exception as e:
                    logger.error(
                        "sequential_debate.resume_tribunal_failed",
                        session_id=session_id,
                        error=str(e),
                    )

            if session.tribunal_verdict and session.tribunal_verdict.get("verdict_text"):
                session.final_verdict = session.tribunal_verdict["verdict_text"]
            else:
                session.final_verdict = self._generate_verdict(session)

            try:
                session.structured_report = await self._generate_structured_report(session)
            except Exception as e:
                logger.error("sequential_debate.resume_report_failed", error=str(e))

            session.status = "completed"
            session.completed_at = datetime.now()

            transcript_path = await self._save_transcript(session)

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

                        try:
                            warehouse_mgr = _get_warehouse_manager()
                            await warehouse_mgr.process_sequential_debate(session_id)
                        except Exception as e:
                            logger.warning(
                                "sequential_debate.resume_warehouse_failed",
                                session_id=session_id,
                                error=str(e),
                            )
            except Exception as e:
                logger.error(
                    "sequential_debate.resume_final_db_error",
                    session_id=session_id,
                    error=str(e),
                )

            logger.info(
                "sequential_debate.resume_completed",
                session_id=session_id,
                total_turns=len(session.turns),
            )

            return session

        except Exception as e:
            session.status = "failed"
            logger.error(
                "sequential_debate.resume_exception",
                session_id=session_id,
                error=str(e),
            )
            try:
                async with AsyncSessionLocal() as db_session:
                    db_debate = await db_session.get(SequentialDebate, session_id)
                    if db_debate:
                        db_debate.status = "failed"
                        await db_session.commit()
            except Exception:
                pass
            return None

    async def run_iterative_debate(
        self,
        session_id: str,
        topic: str,
        agents_config: list[DebateAgent],
        max_iterations: int = 3,
        on_iteration_complete: Callable[[IteracionDebate], None] | None = None,
        on_cruzamiento: Callable[[CruzamientoCritico], None] | None = None,
        mode: str = "iterative",
    ) -> DebateSession:
        """
        Ejecuta un debate iterativo avanzado con múltiples fases:
        1. Análisis: Cada agente presenta su perspectiva inicial
        2. Cruzamiento Crítico: Los agentes se responden entre sí
        3. Validación: Se verifican argumentos y evidencias
        4. Consenso: Se buscan puntos de acuerdo

        El contexto se mantiene entre iteraciones, permitiendo refinamiento progresivo.
        """

        session = DebateSession(id=session_id, topic=topic, status="running", max_iterations=max_iterations)
        self.active_sessions[session_id] = session

        logger.info(
            "sequential_debate.iterative_started",
            session_id=session_id,
            topic=topic,
            max_iterations=max_iterations,
            num_agents=len(agents_config),
        )

        try:
            # ITERACIONES PRINCIPALES
            for iteration_num in range(1, max_iterations + 1):
                session.current_iteration = iteration_num

                logger.info(
                    "sequential_debate.iteration_start",
                    session_id=session_id,
                    iteration=iteration_num,
                )

                # Crear nueva iteración
                current_iteration = IteracionDebate(
                    iteration_number=iteration_num,
                    phase="analysis" if iteration_num == 1 else "refinement",
                    started_at=datetime.now(),
                )

                # FASE 1: ANÁLISIS/REFINAMIENTO (todos los agentes participan)
                await self._run_analysis_phase(session, current_iteration, agents_config, iteration_num)

                # FASE 2: CRUZAMIENTOS CRÍTICOS (si no es la primera iteración)
                if iteration_num > 1:
                    await self._run_cruzamientos_phase(session, current_iteration, agents_config, on_cruzamiento)

                    # FASE 2B: REDUCCIÓN AL ABSURDO (Ronda 2+ para eliminar complacencia)
                    await self._run_reductio_absurdum_phase(session, current_iteration, agents_config, iteration_num)

                # FASE 3: VALIDACIÓN (cada agente valida los argumentos)
                await self._run_validation_phase(session, current_iteration, agents_config)

                # FASE 4: BÚSQUEDA DE CONSENSO
                if iteration_num == max_iterations or self._check_consensus_ready(current_iteration):
                    await self._run_consensus_phase(session, current_iteration, agents_config)
                    session.consensus_reached = True

                # Finalizar iteración
                current_iteration.completed_at = datetime.now()
                session.iterations.append(current_iteration)

                if on_iteration_complete:
                    on_iteration_complete(current_iteration)

                logger.info(
                    "sequential_debate.iteration_complete",
                    session_id=session_id,
                    iteration=iteration_num,
                    turns=len(current_iteration.turns),
                    cruzamientos=len(current_iteration.cruzamientos),
                )

                # Si se alcanzó consenso, terminar
                if session.consensus_reached and iteration_num < max_iterations:
                    logger.info(
                        "sequential_debate.consensus_reached_early",
                        session_id=session_id,
                        iteration=iteration_num,
                    )
                    break

            # GENERAR VEREDICTO FINAL
            session.status = "completed"
            session.completed_at = datetime.now()

            # Usar el tribunal para generar veredicto estructurado
            try:
                tribunal_result = await self.tribunal.deliberate(session)
                session.tribunal_verdict = tribunal_result

                # Generar reporte estructurado
                structured_report = await self._generate_structured_report(session)
                session.structured_report = structured_report

                logger.info(
                    "sequential_debate.iterative_completed",
                    session_id=session_id,
                    total_iterations=len(session.iterations),
                    total_turns=len(session.turns),
                )
                record_debate_completed(
                    total_tokens_out=sum(t.tokens_out for t in session.turns),
                    total_latency_ms=sum(t.latency_ms for t in session.turns),
                    mode="iterative",
                )

            except Exception as e:
                logger.error(
                    "sequential_debate.tribunal_error",
                    session_id=session_id,
                    error=str(e),
                )

            # Guardar transcripción
            await self._save_transcript(session)

            return session

        except Exception as e:
            session.status = "failed"
            logger.error(
                "sequential_debate.iterative_failed",
                session_id=session_id,
                error=str(e),
            )
            raise

    async def _run_analysis_phase(
        self,
        session: DebateSession,
        iteration: IteracionDebate,
        agents_config: list[DebateAgent],
        iteration_num: int,
    ):
        """Ejecuta la fase de análisis donde cada agente presenta su perspectiva"""

        previous_model = None

        for _idx, agent_config in enumerate(agents_config, 1):
            # Liberar modelo anterior
            if previous_model and agent_config.node == "LOCAL" and agent_config.engine == "ollama":
                try:
                    ollama_client = self.engine_manager.engines.get(EngineType.OLLAMA)
                    if ollama_client:
                        await ollama_client.unload_model(previous_model)
                except Exception as e:
                    logger.warning("sequential_debate.unload_failed", error=str(e))

            # Construir prompt con contexto de iteraciones previas
            context = ""
            if iteration_num > 1:
                context = session.get_iteration_context(iteration_num - 1)

            prompt = self._build_iterative_prompt(session.topic, agent_config, iteration_num, context)

            turn = DebateTurn(
                turn_number=len(session.turns) + 1,
                agent=agent_config,
                prompt_sent=prompt,
                started_at=datetime.now(),
            )
            turn.status = "running"

            logger.info(
                "sequential_debate.analysis_turn_start",
                session_id=session.id,
                iteration=iteration_num,
                agent=agent_config.name,
                role=agent_config.role.value,
            )

            try:
                # Ejecutar el turno
                response = await self._run_local_agent(agent_config, prompt, None)

                turn.response_received = response["text"]
                turn.tokens_in = response["tokens_in"]
                turn.tokens_out = response["tokens_out"]
                turn.latency_ms = response["latency_ms"]
                turn.status = "completed"
                turn.completed_at = datetime.now()

                # Actualizar tracking
                if agent_config.node == "LOCAL" and agent_config.engine == "ollama":
                    previous_model = agent_config.model

                session.turns.append(turn)
                iteration.turns.append(turn)

                logger.info(
                    "sequential_debate.analysis_turn_complete",
                    session_id=session.id,
                    agent=agent_config.name,
                    tokens_out=turn.tokens_out,
                )

            except Exception as e:
                turn.status = "failed"
                turn.response_received = f"[Error: {e!s}]"
                logger.error(
                    "sequential_debate.analysis_turn_failed",
                    session_id=session.id,
                    agent=agent_config.name,
                    error=str(e),
                )

    async def _run_cruzamientos_phase(
        self,
        session: DebateSession,
        iteration: IteracionDebate,
        agents_config: list[DebateAgent],
        on_cruzamiento: Callable[[CruzamientoCritico], None] | None,
    ):
        """Ejecuta fase de cruzamientos críticos entre agentes"""

        # Cada agente responde a los argumentos de los demás
        for responder_agent in agents_config:
            # Seleccionar agentes a los que responder (todos excepto sí mismo)
            target_agents = [a for a in agents_config if a.id != responder_agent.id]

            for target_agent in target_agents:
                # Buscar el turno del agente objetivo en esta iteración
                target_turn = None
                for turn in iteration.turns:
                    if turn.agent.id == target_agent.id:
                        target_turn = turn
                        break

                if not target_turn:
                    continue

                # Extraer argumento clave del agente objetivo
                target_argument = target_turn.response_received[:300]

                # Construir prompt de cruzamiento
                cruz_prompt = self._build_cruzamiento_prompt(
                    session.topic, responder_agent, target_agent, target_argument
                )

                try:
                    response = await self._run_local_agent(responder_agent, cruz_prompt, None)

                    cruzamiento = CruzamientoCritico(
                        from_agent=responder_agent.name,
                        to_agent=target_agent.name,
                        target_argument=target_argument,
                        response=response["text"],
                        iteration=iteration.iteration_number,
                    )

                    iteration.cruzamientos.append(cruzamiento)

                    if on_cruzamiento:
                        on_cruzamiento(cruzamiento)

                    logger.info(
                        "sequential_debate.cruzamiento_complete",
                        session_id=session.id,
                        from_agent=responder_agent.name,
                        to_agent=target_agent.name,
                    )

                except Exception as e:
                    logger.warning(
                        "sequential_debate.cruzamiento_failed",
                        session_id=session.id,
                        from_agent=responder_agent.name,
                        to_agent=target_agent.name,
                        error=str(e),
                    )

    async def _run_reductio_absurdum_phase(
        self,
        session: DebateSession,
        iteration: IteracionDebate,
        agents_config: list[DebateAgent],
        iteration_num: int,
    ):
        """
        FASE 2B: Reducción al Absurdo (Ronda 2+)

        Aplica técnica lógica de reducción al absurdo para:
        - Eliminar sesgos de complacencia
        - Desafiar supuestos no cuestionados
        - Llevar proposiciones a su límite lógico
        - Identificar contradicciones

        Ejecutada solo en ronda 2+
        """

        logger.info(
            "sequential_debate.reductio_absurdum_phase_start",
            session_id=session.id,
            iteration=iteration_num,
        )

        # Extraer puntos de consenso de turnos anteriores
        consensus_points = []
        for turn in iteration.turns:
            # Proposiciones que aparecen en el debate sin haber sido cuestionadas
            propositions = self.reductio_engine.extract_propositions_from_text(turn.response_received)
            consensus_points.extend(propositions)

        # Construir historial del debate para análisis de complacencia
        debate_history = "\n\n".join([turn.response_received[:500] for turn in iteration.turns])

        # Analizar riesgo de complacencia
        complacency_scan: ComplacencyScan = self.reductio_engine.analyze_consensus_points(
            consensus_points=consensus_points,
            dissent_points=[],  # No hay puntos explícitos de desacuerdo aún
            debate_history=debate_history,
            iteration_number=iteration_num,
        )

        logger.info(
            "sequential_debate.complacency_analysis",
            session_id=session.id,
            complacency_risk=f"{complacency_scan.overall_complacency_risk:.0%}",
            weak_assumptions=len(complacency_scan.weak_assumptions),
            unquestioned_premises=len(complacency_scan.unquestioned_premises),
        )

        # Si hay riesgo alto de complacencia, ejecutar desafíos
        if complacency_scan.overall_complacency_risk > 0.4:
            logger.info(
                "sequential_debate.high_complacency_detected",
                session_id=session.id,
                risk=f"{complacency_scan.overall_complacency_risk:.0%}",
            )

            # Seleccionar pares de agentes para desafíos cruzados
            for i, challenger_agent in enumerate(agents_config):
                if i + 1 >= len(agents_config):
                    break

                target_agent = agents_config[i + 1]

                # Generar prompt de desafío por reducción al absurdo
                weak_points = complacency_scan.weak_assumptions[:3]

                if not weak_points:
                    continue

                # Construir prompt de desafío específico para este par
                try:
                    proof = await self.reductio_engine.run_absurdum_challenge_phase(
                        topic=session.topic,
                        consensus_points=weak_points,
                        debate_history=debate_history,
                        challenging_agent=challenger_agent,
                        target_agent=target_agent,
                        generate_func=lambda agent, prompt: self._generate_absurdum_response(agent, prompt),
                    )
                    if not proof:
                        continue

                    await self._persist_reductio_absurdum_proof(
                        debate_id=session.id,
                        iteration_number=iteration_num,
                        complacency_scan=complacency_scan,
                        proof=proof,
                    )

                    # Registrar el desafío como un cruzamiento especial
                    abs_cruzamiento = CruzamientoCritico(
                        from_agent=f"{challenger_agent.name} (Reductio)",
                        to_agent=target_agent.name,
                        target_argument=proof.proposition,
                        response=proof.extreme_case,
                        iteration=iteration_num,
                    )

                    iteration.cruzamientos.append(abs_cruzamiento)

                    logger.info(
                        "sequential_debate.absurdum_challenge_complete",
                        session_id=session.id,
                        challenger=challenger_agent.name,
                        target=target_agent.name,
                        contradiction_found=bool(proof.contradiction),
                    )

                except Exception as e:
                    logger.warning(
                        "sequential_debate.absurdum_challenge_failed",
                        session_id=session.id,
                        challenger=challenger_agent.name,
                        error=str(e),
                    )

        else:
            logger.info(
                "sequential_debate.low_complacency_risk",
                session_id=session.id,
                risk=f"{complacency_scan.overall_complacency_risk:.0%}",
                skipping_reductio="Fase de Reducción al Absurdo no necesaria",
            )

        logger.info(
            "sequential_debate.reductio_absurdum_phase_complete",
            session_id=session.id,
            iteration=iteration_num,
            recommendations_count=len(complacency_scan.recommendations),
        )

    async def _generate_absurdum_response(self, agent: DebateAgent, prompt: str) -> str:
        """Adaptador simple para integrar el motor reductio con el runner local del debate."""
        response = await self._run_local_agent(agent, prompt, None)
        return response["text"]

    async def _run_validation_phase(
        self,
        session: DebateSession,
        iteration: IteracionDebate,
        agents_config: list[DebateAgent],
    ):
        """Fase de validación donde agentes verifican argumentos"""

        # Crear agentes validadores (cambio de rol temporal)
        validators = []
        for agent_config in agents_config:
            validator = DebateAgent(
                id=f"validator_{agent_config.id}",
                name=f"Validador {agent_config.name}",
                role=AgentRole.VALIDATOR,
                node=agent_config.node,
                engine=agent_config.engine,
                model=agent_config.model,
                provider=agent_config.provider,
                system_prompt="Valida la coherencia lógica, evidencia y solidez de los argumentos presentados.",
                temperature=0.3,
                max_tokens=500,
            )
            validators.append(validator)

        # Cada validador revisa todos los argumentos de la iteración
        for validator in validators:
            arguments_to_validate = "\n\n".join(
                [f"{turn.agent.name}: {turn.response_received[:250]}" for turn in iteration.turns]
            )

            validation_prompt = f"""# FASE DE VALIDACIÓN

Tema: {session.topic}

## Argumentos a Validar:
{arguments_to_validate}

## Tu Tarea como Validador
1. Identifica fortalezas en los argumentos
2. Señala debilidades lógicas o falta de evidencia
3. Evalúa la coherencia entre las diferentes perspectivas
4. Asigna una puntuación de validez (1-10) a cada argumento

Responde de manera concisa y constructiva."""

            try:
                response = await self._run_local_agent(validator, validation_prompt, None)

                # Extraer puntos de acuerdo y desacuerdo
                validation_text = response["text"]

                # Análisis simple para identificar consensos y disensos
                if "consenso" in validation_text.lower() or "acuerdo" in validation_text.lower():
                    iteration.consensus_points.append(f"Validador {validator.name}: {validation_text[:200]}")

                if "desacuerdo" in validation_text.lower() or "discrepancia" in validation_text.lower():
                    iteration.disagreement_points.append(f"Validador {validator.name}: {validation_text[:200]}")

                logger.info(
                    "sequential_debate.validation_complete",
                    session_id=session.id,
                    validator=validator.name,
                )

            except Exception as e:
                logger.warning(
                    "sequential_debate.validation_failed",
                    session_id=session.id,
                    validator=validator.name,
                    error=str(e),
                )

    async def _run_consensus_phase(
        self,
        session: DebateSession,
        iteration: IteracionDebate,
        agents_config: list[DebateAgent],
    ):
        """Fase final de búsqueda de consenso"""

        # Crear agente consensuador
        consensus_agent = DebateAgent(
            id="consensus_builder",
            name="Consensuador",
            role=AgentRole.CONSENSUS,
            node="LOCAL",
            engine="ollama",
            model="mistral:7b",
            provider="mistral",
            system_prompt="Tu objetivo es identificar puntos de acuerdo y proponer un marco de consenso.",
            temperature=0.4,
            max_tokens=800,
        )

        # Compilar todo el contexto
        full_context = session.get_iteration_context(iteration.iteration_number)

        consensus_prompt = f"""# FASE DE CONSENSO

Tema: {session.topic}

## Contexto del Debate:
{full_context}

## Puntos de Acuerdo Identificados:
{"\n".join(iteration.consensus_points) if iteration.consensus_points else "Aún no se han identificado puntos de acuerdo claros."}

## Puntos de Desacuerdo:
{"\n".join(iteration.disagreement_points) if iteration.disagreement_points else "No hay desacuerdos significativos registrados."}

## Tu Tarea
1. Identifica los puntos de acuerdo fundamentales entre todos los participantes
2. Propone un marco de consenso que integre las perspectivas válidas
3. Señala áreas donde es necesario más debate o investigación
4. Formula recomendaciones concretas basadas en el consenso alcanzado

Este es el momento de sintetizar todo el debate en conclusiones accionables."""

        try:
            response = await self._run_local_agent(consensus_agent, consensus_prompt, None)

            # Agregar como un turno especial de consenso
            consensus_turn = DebateTurn(
                turn_number=len(session.turns) + 1,
                agent=consensus_agent,
                prompt_sent=consensus_prompt,
                response_received=response["text"],
                tokens_in=response["tokens_in"],
                tokens_out=response["tokens_out"],
                latency_ms=response["latency_ms"],
                status="completed",
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )

            session.turns.append(consensus_turn)
            iteration.turns.append(consensus_turn)
            iteration.consensus_points.append(response["text"])

            logger.info(
                "sequential_debate.consensus_complete",
                session_id=session.id,
                iteration=iteration.iteration_number,
                tokens_out=response["tokens_out"],
            )

        except Exception as e:
            logger.error(
                "sequential_debate.consensus_failed",
                session_id=session.id,
                error=str(e),
            )

    def _check_consensus_ready(self, iteration: IteracionDebate) -> bool:
        """Verifica si hay indicios de que se puede alcanzar consenso"""
        # Si hay más puntos de acuerdo que desacuerdo, y son sustanciales
        return (
            len(iteration.consensus_points) > len(iteration.disagreement_points)
            and len(iteration.consensus_points) >= 2
        )

    def _build_iterative_prompt(self, topic: str, agent: DebateAgent, iteration: int, context: str) -> str:
        """Construye prompt para fase iterativa"""

        role_specific_instructions = {
            AgentRole.ANALYST: "Presenta tu análisis inicial del tema desde tu perspectiva especializada.",
            AgentRole.CRITIC: "Identifica debilidades en los argumentos presentados y ofrece contrapuntos constructivos.",
            AgentRole.VALIDATOR: "Verifica la solidez lógica y factual de los argumentos.",
            AgentRole.CONSENSUS: "Busca puntos de acuerdo y propone síntesis.",
            AgentRole.SYNTHESIZER: "Integra las diferentes perspectivas en una visión coherente.",
            AgentRole.REFINER: "Refina y mejora las propuestas existentes.",
        }

        instruction = role_specific_instructions.get(agent.role, "Contribuye con tu perspectiva única al debate.")

        context_section = ""
        if context and iteration > 1:
            context_section = f"""
## Contexto de Iteraciones Previas
{context}

## Instrucción Especial
Esta es la iteración {iteration}. Debes:
1. Considerar los argumentos previos
2. Refinar o matizar tu posición según el debate
3. Responder directamente a las críticas si las hay
4. Avanzar hacia un consenso sin sacrificar la rigurosidad
"""

        return f"""# DEBATE ITERATIVO - Iteración {iteration}

Tema: {topic}

## Tu Identidad
Eres: {agent.name}
Rol: {agent.role.value}
Modelo: {agent.model} ({agent.provider})

## Tu Especialización
{agent.system_prompt}

{context_section}

## Tu Tarea en esta Iteración
{instruction}

Proporciona un análisis detallado, fundamentado y constructivo."""

    def _build_cruzamiento_prompt(
        self,
        topic: str,
        responder: DebateAgent,
        target: DebateAgent,
        target_argument: str,
    ) -> str:
        """Construye prompt para cruzamiento crítico"""

        return f"""# CRUZAMIENTO CRÍTICO

Tema: {topic}

## Tu Identidad
Eres: {responder.name} ({responder.role.value})

## Argumento a Responder
**{target.name}** dice:
"{target_argument}"

## Tu Tarea
Responde directamente a este argumento:
1. Identifica sus fortalezas y debilidades
2. Ofrece contra-argumentos específicos si hay debilidades
3. Construye sobre las fortalezas si las hay
4. Mantén un tono respetuoso pero riguroso

Tu respuesta debe ser concisa (150-250 tokens) y enfocada en este argumento específico."""


# Configuraciones predefinidas de debates
def get_standard_debate_config(topic: str) -> list[DebateAgent]:
    """Configuración estándar: 3 locales + 1 cloud"""
    return [
        # 1. Análisis inicial - Meta (llama3)
        DebateAgent(
            id="analyst_llama3",
            name="Analista Meta",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3:8b",
            provider="meta",
            system_prompt="Analiza el tema propuesto desde una perspectiva técnica y estructurada. "
            "Identifica los puntos clave, supuestos y posibles enfoques. "
            "Responde en español, máximo 500 palabras.",
            temperature=0.7,
            max_tokens=1000,
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
            "Sé constructivo pero riguroso. Responde en español, máximo 500 palabras.",
            temperature=0.8,
            max_tokens=1000,
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
            "Responde en español, máximo 500 palabras.",
            temperature=0.6,
            max_tokens=1000,
        ),
        # 4. Refinamiento - DeepSeek (local reasoning)
        DebateAgent(
            id="refiner_deepseek",
            name="Refinador DeepSeek",
            role=AgentRole.REFINER,
            node="LOCAL",
            engine="ollama",
            model="deepseek-r1:7b",
            provider="deepseek",
            system_prompt="Refina y mejora la síntesis anterior. Considera perspectivas adicionales "
            "y elabora una conclusión bien fundamentada. "
            "Responde en español, máximo 600 palabras.",
            temperature=0.5,
            max_tokens=1200,
        ),
    ]


def get_local_only_config(topic: str) -> list[DebateAgent]:
    """Configuración solo local: 4 modelos distintos"""
    return [
        DebateAgent(
            id="analyst_llama3",
            name="Analista Meta (Llama3)",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3:8b",
            provider="meta",
            system_prompt="Análisis técnico profundo del tema. Enfoque práctico y estructurado. Máximo 500 palabras.",
            temperature=0.7,
            max_tokens=1000,
        ),
        DebateAgent(
            id="critic_mistral",
            name="Crítico Mistral",
            role=AgentRole.CRITIC,
            node="LOCAL",
            engine="ollama",
            model="mistral:7b",
            provider="mistral",
            system_prompt="Crítica constructiva y rigurosa del análisis. Identificar debilidades. Máximo 500 palabras.",
            temperature=0.8,
            max_tokens=1000,
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
            "Máximo 500 palabras.",
            temperature=0.6,
            max_tokens=1000,
        ),
        DebateAgent(
            id="refiner_deepseek",
            name="Refinador DeepSeek",
            role=AgentRole.REFINER,
            node="LOCAL",
            engine="ollama",
            model="deepseek-r1:7b",
            provider="deepseek",
            system_prompt="Refinamiento final con reasoning. Considera implicaciones profundas. Máximo 600 palabras.",
            temperature=0.5,
            max_tokens=1200,
        ),
    ]


def get_cloud_ollama_config(topic: str) -> list[DebateAgent]:
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
            max_tokens=1000,
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
            max_tokens=800,
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
            max_tokens=1200,
        ),
    ]


def get_hybrid_rotation_config(topic: str) -> list[DebateAgent]:
    """
    Configuración híbrida Master/Worker con rotación inteligente.

    Estrategia:
    - OpenRouter (Master) SOLO en turnos clave (analista, sintetizador)
    - Ollama/Worker en TODOS los demás turnos para evitar rate limits
    - NUNCA dos turnos consecutivos con OpenRouter
    - Delay mínimo de 30s entre llamadas a OpenRouter

    Patrón: [OpenRouter] -> [Worker] -> [Worker] -> [OpenRouter] -> [Worker] -> [Worker]
    """
    return [
        # TURNO 1: OpenRouter (Master) - Análisis inicial de alta calidad
        DebateAgent(
            id="analyst_openrouter",
            name="Analista OpenRouter",
            role=AgentRole.ANALYST,
            node="CLOUD",
            engine="openrouter",
            model="deepseek/deepseek-v4-flash:free",
            provider="deepseek",
            system_prompt="Analiza el tema propuesto desde una perspectiva técnica y estructurada. "
            "Identifica los puntos clave, supuestos y posibles enfoques. "
            "Responde en español, máximo 500 palabras.",
            temperature=0.7,
            max_tokens=1000,
        ),
        # TURNO 2: Worker (Ollama) - Crítica local
        DebateAgent(
            id="critic_ollama",
            name="Crítico Mistral (Worker)",
            role=AgentRole.CRITIC,
            node="LOCAL",
            engine="ollama",
            model="mistral:7b",
            provider="mistral",
            system_prompt="Examina críticamente el análisis anterior. Identifica debilidades lógicas, "
            "supuestos no verificados y alternativas no consideradas. "
            "Sé constructivo pero riguroso. Responde en español, máximo 500 palabras.",
            temperature=0.8,
            max_tokens=1000,
        ),
        # TURNO 3: Worker (Ollama) - Síntesis local
        DebateAgent(
            id="synth_ollama",
            name="Sintetizador Qwen (Worker)",
            role=AgentRole.SYNTHESIZER,
            node="LOCAL",
            engine="ollama",
            model="qwen2.5:3b",
            provider="alibaba",
            system_prompt="Sintetiza los argumentos presentados hasta ahora. Encuentra puntos de "
            "acuerdo y desacuerdo. Propone un marco integrador. "
            "Responde en español, máximo 500 palabras.",
            temperature=0.6,
            max_tokens=1000,
        ),
        # TURNO 4: OpenRouter (Master) - Refinamiento de alta calidad
        DebateAgent(
            id="refiner_openrouter",
            name="Refinador OpenRouter",
            role=AgentRole.REFINER,
            node="CLOUD",
            engine="openrouter",
            model="google/gemma-4-26b-a4b-it:free",
            provider="google",
            system_prompt="Refina y mejora la síntesis anterior. Considera perspectivas adicionales "
            "y elabora una conclusión bien fundamentada. "
            "Responde en español, máximo 600 palabras.",
            temperature=0.5,
            max_tokens=1200,
        ),
        # TURNO 5: Worker (Ollama) - Validación local
        DebateAgent(
            id="validator_ollama",
            name="Validador Llama3 (Worker)",
            role=AgentRole.VALIDATOR,
            node="LOCAL",
            engine="ollama",
            model="llama3:8b",
            provider="meta",
            system_prompt="Valida la solidez lógica de todos los argumentos presentados. "
            "Verifica consistencia interna y externa. Responde en español, máximo 400 palabras.",
            temperature=0.4,
            max_tokens=800,
        ),
        # TURNO 6: Worker (Ollama) - Moderación local
        DebateAgent(
            id="moderator_ollama",
            name="Moderador Gemma (Worker)",
            role=AgentRole.MODERATOR,
            node="LOCAL",
            engine="ollama",
            model="gemma:7b",
            provider="google",
            system_prompt="Modera el debate, resume las posiciones encontradas y propone "
            "areas de consenso. Responde en español, máximo 500 palabras.",
            temperature=0.6,
            max_tokens=1000,
        ),
    ]


def get_smart_rotation_config(topic: str, max_turns: int = 6, mode: str = "hybrid_rotation") -> list[DebateAgent]:
    """
    Genera configuracion de debate con asignacion inteligente de modelos.
    Usa RoleMatcher para seleccionar el mejor modelo por rol y plataforma.
    """
    from backend.engine.debate_models import DebateAgent

    matcher = RoleMatcher()
    agents_config = matcher.generate_debate_config(topic=topic, max_turns=max_turns, mode=mode)

    agents = []
    for ac in agents_config:
        agents.append(
            DebateAgent(
                id=ac["id"],
                name=ac["name"],
                role=AgentRole(ac["role"]),
                node=ac["node"],
                engine=ac["engine"],
                model=ac["model"],
                provider=ac.get("provider", "unknown"),
                system_prompt=ac["system_prompt"],
                temperature=ac["temperature"],
                max_tokens=ac["max_tokens"],
            )
        )

    return agents
