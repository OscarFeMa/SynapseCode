"""
Synapse Council v2.0 - Agent Orchestrator
Orquesta llamadas a agentes con paralelismo, persistencia y cross-references
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
from dataclasses import dataclass
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from backend.engine.local_engine_manager import LocalEngineManager, EngineType
from backend.adapters.openrouter import OpenRouterClient
from backend.adapters.web_agent import WebAgentClient
from backend.database.models import AgentCall, CrossReference
from backend.config import get_settings

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
        on_token: Optional[Callable[[str], None]] = None
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
        
        logger.info("call_agent.starting_generation", slot=config.slot, node=config.node, engine=config.engine, model=config.model)
        
        try:
            # Seleccionar motor y ejecutar
            response_parts = []
            
            if config.node == "LOCAL":
                engine_type = EngineType(config.engine)
                logger.info("call_agent.local_engine_selected", engine_type=engine_type.value)
                
                # Forzar stream=True siempre para asegurar consumo completo del generador
                logger.info("call_agent.calling_generate", model=config.model, prompt_preview=user_prompt[:50])
                token_count = 0
                async for token in self.local_manager.generate(
                    engine_type=engine_type,
                    model=config.model,
                    prompt=user_prompt,
                    system=system_prompt,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    stream=True
                ):
                    token_count += 1
                    response_parts.append(token)
                    if on_token:
                        on_token(token)
                logger.info("call_agent.generate_completed", tokens_yielded=token_count, response_length=len("".join(response_parts)))
                        
            elif config.node == "CLOUD":
                if not self.openrouter:
                    raise RuntimeError("OpenRouter not configured")
                    
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                async for token in self.openrouter.chat_completion(
                    model=config.model,
                    messages=messages,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    stream=on_token is not None
                ):
                    response_parts.append(token)
                    if on_token:
                        on_token(token)
                        
            elif config.node == "WEB_AGENT":
                # Web Agent usa Playwright (no streaming)
                result = await self.web_agent.query_chatgpt(user_prompt)
                response_parts.append(result)
            
            # Calcular métricas
            response_text = "".join(response_parts)
            completed_at = datetime.utcnow()
            latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # Estimación de tokens (len/4 es ~90% preciso vs split que es ~75%)
            tokens_in = len(system_prompt) // 4 + len(user_prompt) // 4
            tokens_out = len(response_text) // 4
            
            # Actualizar en DB
            agent_call.status = "COMPLETED"
            agent_call.response = response_text
            agent_call.tokens_in = tokens_in
            agent_call.tokens_out = tokens_out
            agent_call.latency_ms = latency_ms
            agent_call.completed_at = completed_at
            await db_session.commit()
            
            logger.info(
                "agent_call.completed",
                call_id=call_id,
                agent_slot=config.slot,
                latency_ms=latency_ms,
                tokens_out=tokens_out,
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
        on_agent_token: Optional[Callable[[str, str], None]] = None  # (slot, token)
    ) -> Dict[str, AgentResult]:
        """
        Llama múltiples agentes secuencialmente (temporalmente para aislar problema de concurrencia)
        Retorna dict: {slot: AgentResult}
        """

        output = {}
        for config in agent_configs:
            system_prompt, user_prompt = prompts.get(config.slot, ("", ""))

            def token_callback(token: str):
                if on_agent_token:
                    on_agent_token(config.slot, token)

            result = await self.call_agent(
                session_id=session_id,
                round_id=round_id,
                round_number=round_number,
                phase=phase,
                config=config,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                db_session=db_session,
                on_token=token_callback if on_agent_token else None
            )

            output[config.slot] = result

        return output
    
    async def create_cross_references(
        self,
        consumer_call_id: str,
        source_call_ids: List[str],
        context_type: str,
        db_session: AsyncSession
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
    
    def check_failure_threshold(
        self,
        results: Dict[str, AgentResult],
        threshold_percent: float = 0.5
    ) -> bool:
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
