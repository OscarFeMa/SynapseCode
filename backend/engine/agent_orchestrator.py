"""
Synapse Council v2.0 - Agent Orchestrator
Orquesta llamadas a agentes con paralelismo, persistencia y cross-references
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.openrouter import OpenRouterClient
from backend.adapters.web_agent import WebAgentClient
from backend.config import get_settings
from backend.database.local_db import AsyncSessionLocal
from backend.database.models import AgentCall, CrossReference
from backend.engine.intervention_taxonomy import detect_intervention_type
from backend.engine.local_engine_manager import EngineType, LocalEngineManager
from backend.engine.quality_monitor import evaluate_response
from backend.engine.reputation_service import get_reputation_service

settings = get_settings()
logger = structlog.get_logger()


@dataclass
class AgentConfig:
    """Configuración de un agente"""

    slot: str
    node: str  # LOCAL, CLOUD, WEB_AGENT
    engine: str  # ollama, lm_studio, jan, openrouter, web_agent
    model: str
    role_label: str
    temperature: float = 0.7
    max_tokens: int = 1000


@dataclass
class AgentResult:
    """Resultado de una llamada a agente"""

    call_id: str
    slot: str
    node: str
    status: str  # COMPLETED, FAILED, TIMEOUT
    response: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    error_message: Optional[str] = None
    reputation_score: float = 0.5  # Score EMA del modelo+rol
    model: str = ""
    role: str = ""


class AgentOrchestrator:
    """
    Orquestador de agentes:
    - Paralelismo con asyncio.gather()
    - Persistencia en base de datos
    - Cross-references entre agentes
    - Manejo de errores por agente
    """

    def __init__(self):
        self._local_manager = None
        self._openrouter = None
        self._web_agent = None
        self._master_ollama = None
        self._gemini = None
        self._groq = None
        self._deepseek = None

    @property
    def local_manager(self):
        if self._local_manager is None:
            self._local_manager = LocalEngineManager()
        return self._local_manager

    @property
    def openrouter(self):
        if self._openrouter is None:
            self._openrouter = OpenRouterClient() if settings.OPENROUTER_API_KEY else None
        return self._openrouter

    @property
    def master_ollama(self):
        if self._master_ollama is None:
            # Cliente para el Ollama local del Master (usado para Cloud models)
            from backend.adapters.ollama import OllamaClient

            self._master_ollama = OllamaClient(base_url=settings.OLLAMA_BASE_URL)
        return self._master_ollama

    @property
    def gemini(self):
        if self._gemini is None:
            from backend.adapters.gemini import GeminiClient

            self._gemini = GeminiClient() if settings.GEMINI_API_KEY else None
        return self._gemini

    @property
    def groq(self):
        if self._groq is None:
            from backend.adapters.groq import GroqClient

            self._groq = GroqClient() if settings.GROQ_API_KEY else None
        return self._groq

    @property
    def deepseek(self):
        if self._deepseek is None:
            from backend.adapters.deepseek import DeepSeekClient

            self._deepseek = DeepSeekClient() if settings.DEEPSEEK_API_KEY else None
        return self._deepseek

    @property
    def web_agent(self):
        if self._web_agent is None:
            self._web_agent = WebAgentClient(
                enabled=settings.WEB_AGENT_ENABLED,
                browser=settings.WEB_AGENT_BROWSER,
                headless=settings.WEB_AGENT_HEADLESS,
            )
        return self._web_agent

    async def call_agent(
        self,
        session_id: str,
        round_id: str,
        round_number: int,
        phase: str,
        config: AgentConfig,
        system_prompt: str,
        user_prompt: str,
        db_session: AsyncSession,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AgentResult:
        """
        Llama a un agente individual con persistencia completa
        """
        call_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        start_time = asyncio.get_event_loop().time()

        # Crear registro en DB
        agent_call = AgentCall(
            id=call_id,
            session_id=session_id,
            round_id=round_id,
            round_number=round_number,
            phase=phase,
            agent_slot=config.slot,
            node=config.node,
            engine=config.engine,
            model_name=config.model,
            role_label=config.role_label,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            status="STREAMING" if on_token else "PENDING",
            started_at=started_at,
        )

        db_session.add(agent_call)
        await db_session.commit()

        logger.info(
            "agent_call.started",
            call_id=call_id,
            session_id=session_id,
            agent_slot=config.slot,
            phase=phase,
        )

        logger.info(
            "call_agent.starting_generation",
            slot=config.slot,
            node=config.node,
            engine=config.engine,
            model=config.model,
        )

        try:
            # Seleccionar motor y ejecutar
            response_parts = []
            tokens_in = len(user_prompt.split())  # Aproximación
            tokens_out = 0

            if config.node == "LOCAL":
                engine_type = EngineType(config.engine)
                logger.info("call_agent.local_engine_selected", engine_type=engine_type.value)

                # Forzar stream=True siempre para asegurar consumo completo del generador
                logger.info(
                    "call_agent.calling_generate",
                    model=config.model,
                    prompt_preview=user_prompt[:50],
                )

                # Generar con timeout para evitar bloqueos infinitos
                token_count = 0
                try:
                    # Usar wait_for para timeout externo si el generador se cuelga
                    async for token in self.local_manager.generate(
                        engine_type=engine_type,
                        model=config.model,
                        prompt=user_prompt,
                        system=system_prompt,
                        temperature=config.temperature,
                        max_tokens=config.max_tokens,
                        stream=True,
                    ):
                        if not token or not token.strip():
                            continue
                        token_count += 1
                        tokens_out += 1
                        response_parts.append(token)
                        if on_token:
                            on_token(token)
                    logger.info(
                        "call_agent.generate_completed",
                        tokens_yielded=token_count,
                        response_length=len("".join(response_parts)),
                    )
                except Exception as e:
                    logger.error(
                        "call_agent.local_generation_error",
                        model=config.model,
                        error=str(e),
                    )
                    raise

            elif config.node == "CLOUD":
                if config.engine == "ollama":
                    # Ollama Cloud (ejecutado via Master local)
                    logger.info("call_agent.ollama_cloud.start", model=config.model)
                    async for token in self.master_ollama.generate(
                        model=config.model,
                        prompt=user_prompt,
                        system=system_prompt,
                        options={
                            "temperature": config.temperature,
                            "num_predict": config.max_tokens,
                        },
                        stream=True,
                    ):
                        tokens_out += 1
                        response_parts.append(token)
                        if on_token:
                            on_token(token)

                elif config.engine == "openrouter":
                    # OpenRouter
                    if not self.openrouter:
                        raise RuntimeError("OpenRouter not configured")

                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]

                    async for token in self.openrouter.chat_completion(
                        model=config.model,
                        messages=messages,
                        temperature=config.temperature,
                        max_tokens=config.max_tokens,
                        stream=on_token is not None,
                    ):
                        response_parts.append(token)
                        tokens_out += 1
                        if on_token and token:
                            on_token(token)

                elif config.engine == "gemini":
                    # Google Gemini API
                    if not self.gemini:
                        raise RuntimeError("Gemini API not configured")

                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]
                    async for token in self.gemini.chat_completion(
                        model=config.model,
                        messages=messages,
                        temperature=config.temperature,
                        max_tokens=config.max_tokens,
                        stream=True,
                    ):
                        response_parts.append(token)
                        tokens_out += 1
                        if on_token:
                            on_token(token)

                elif config.engine == "groq":
                    # Groq API
                    if not self.groq:
                        raise RuntimeError("Groq API not configured")

                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]
                    async for token in self.groq.chat_completion(
                        model=config.model,
                        messages=messages,
                        temperature=config.temperature,
                        max_tokens=config.max_tokens,
                        stream=True,
                    ):
                        response_parts.append(token)
                        tokens_out += 1
                        if on_token:
                            on_token(token)

                elif config.engine == "deepseek":
                    # DeepSeek API
                    if not self.deepseek:
                        raise RuntimeError("DeepSeek API not configured")

                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]
                    async for token in self.deepseek.chat_completion(
                        model=config.model,
                        messages=messages,
                        temperature=config.temperature,
                        max_tokens=config.max_tokens,
                        stream=True,
                    ):
                        response_parts.append(token)
                        tokens_out += 1
                        if on_token:
                            on_token(token)
                else:
                    raise RuntimeError(f"Unsupported cloud engine: {config.engine}")

            elif config.node == "WEB_AGENT":
                # Web Agent usa Playwright (no streaming)
                result = await self.web_agent.query_chatgpt(user_prompt)
                response_parts.append(result)

            # Calcular métricas
            response_text = "".join(response_parts)
            completed_at = datetime.utcnow()
            latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            # Métricas avanzadas (v2.1)
            quality_score, _ = evaluate_response(response_text, config.slot)
            intervention_type = detect_intervention_type(response_text, config.slot)

            # Obtener score de reputación
            rep_service = get_reputation_service()
            rep_score = await rep_service.get_score(config.model, config.role_label)

            # Actualizar en DB
            agent_call.status = "COMPLETED"
            agent_call.response = response_text
            agent_call.tokens_in = tokens_in
            agent_call.tokens_out = tokens_out
            agent_call.latency_ms = latency_ms
            agent_call.quality_score = quality_score
            agent_call.intervention_type = intervention_type
            agent_call.completed_at = completed_at
            await db_session.commit()

            logger.info(
                "agent_call.completed",
                call_id=call_id,
                agent_slot=config.slot,
                latency_ms=latency_ms,
                tokens_out=tokens_out,
                reputation_score=round(rep_score.reputation_score, 3),
            )

            return AgentResult(
                call_id=call_id,
                slot=config.slot,
                node=config.node,
                status="COMPLETED",
                response=response_text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                reputation_score=rep_score.reputation_score,
                model=config.model,
                role=config.role_label,
            )

        except asyncio.TimeoutError:
            agent_call.status = "TIMEOUT"
            agent_call.error_message = "Request timeout"
            agent_call.completed_at = datetime.utcnow()
            await db_session.commit()

            logger.error(
                "agent_call.timeout",
                call_id=call_id,
                agent_slot=config.slot,
            )

            return AgentResult(
                call_id=call_id,
                slot=config.slot,
                node=config.node,
                status="TIMEOUT",
                error_message="Request timeout",
            )

        except Exception as e:
            error_msg = str(e)
            agent_call.status = "FAILED"
            agent_call.error_message = error_msg
            agent_call.completed_at = datetime.utcnow()
            await db_session.commit()

            logger.error(
                "agent_call.failed",
                call_id=call_id,
                agent_slot=config.slot,
                error=error_msg,
            )

            return AgentResult(
                call_id=call_id,
                slot=config.slot,
                node=config.node,
                status="FAILED",
                error_message=error_msg,
            )

    async def call_agents_parallel(
        self,
        session_id: str,
        round_id: str,
        round_number: int,
        phase: str,
        agent_configs: List[AgentConfig],
        prompts: Dict[str, tuple],  # {slot: (system_prompt, user_prompt)}
        db_session: AsyncSession,
        on_agent_token: Optional[Callable[[str, str], None]] = None,  # (slot, token)
    ) -> Dict[str, AgentResult]:
        """
        Llama múltiples agentes en PARALELO con asyncio.gather().
        Retorna dict: {slot: AgentResult}
        """

        async def _call_one(config: AgentConfig) -> tuple[str, AgentResult]:
            system_prompt, user_prompt = prompts.get(config.slot, ("", ""))

            def token_callback(token: str):
                if on_agent_token:
                    on_agent_token(config.slot, token, config.model, phase)

            async with AsyncSessionLocal() as agent_db_session:
                result = await self.call_agent(
                    session_id=session_id,
                    round_id=round_id,
                    round_number=round_number,
                    phase=phase,
                    config=config,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    db_session=agent_db_session,
                    on_token=token_callback if on_agent_token else None,
                )
            return config.slot, result

        tasks = [_call_one(cfg) for cfg in agent_configs]
        results = await asyncio.gather(*tasks)

        output: Dict[str, AgentResult] = {slot: res for slot, res in results}
        return output

    async def create_cross_references(
        self,
        consumer_call_id: str,
        source_call_ids: List[str],
        context_type: str,
        db_session: AsyncSession,
    ):
        """
        Crea registros de cross-reference en la base de datos
        """
        for source_id in source_call_ids:
            cross_ref = CrossReference(
                id=str(uuid.uuid4()),
                consumer_call_id=consumer_call_id,
                source_call_id=source_id,
                context_type=context_type,
            )
            db_session.add(cross_ref)

        await db_session.commit()

        logger.debug(
            "cross_references.created",
            consumer=consumer_call_id,
            sources=len(source_call_ids),
            type=context_type,
        )

    def check_failure_threshold(self, results: Dict[str, AgentResult], threshold_percent: float = 0.5) -> bool:
        """
        Verifica si se superó el umbral de fallos (>50% por defecto)
        Retorna True si se debe abortar la sesión
        """
        if not results:
            return True

        total = len(results)
        failed = sum(1 for r in results.values() if r.status in ["FAILED", "TIMEOUT"])

        failure_rate = failed / total
        should_abort = failure_rate > threshold_percent

        if should_abort:
            logger.error(
                "failure_threshold_exceeded",
                failed=failed,
                total=total,
                rate=failure_rate,
            )

        return should_abort
