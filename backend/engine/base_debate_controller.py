"""
Synapse Council v2.0 - Base Debate Controller

Jerarquía base para todos los controladores de debate.
Elimina duplicación de lógica común entre:
- session_manager.py / round_controller.py (legacy v1)
- sequential_debate_controller.py (v2)
- consensus_debate_controller.py (v2)
- ultra_debate_controller.py (v2)
"""

import os
import uuid
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Protocol
from dataclasses import dataclass, field
from enum import Enum
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.local_db import AsyncSessionLocal

settings = get_settings()
logger = structlog.get_logger()


# ============================================================================
# ENUMS Y DATACLASSES BASE
# ============================================================================

class DebateStatus(Enum):
    """Estados comunes de un debate"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CONSENSUS_REACHED = "consensus_reached"
    CONSENSUS_FAILED = "consensus_failed"


class AgentRole(Enum):
    """Roles disponibles para agentes en el debate"""
    ANALYST = "analyst"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"
    REFINER = "refiner"
    MODERATOR = "moderator"
    VALIDATOR = "validator"
    CONSENSUS = "consensus"
    TRIBUNAL = "tribunal"


@dataclass
class AgentConfig:
    """Configuración base de un agente"""
    id: str
    node: str  # LOCAL | CLOUD
    engine: str  # ollama | openrouter | lm_studio | etc
    model: str
    name: str
    role: AgentRole = AgentRole.ANALYST
    max_tokens: int = 1000
    temperature: float = 0.7
    provider: str = "unknown"


@dataclass
class DebateMetrics:
    """Métricas comunes de un debate"""
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_latency_ms: int = 0
    turns_completed: int = 0
    turns_failed: int = 0
    
    @property
    def avg_latency_ms(self) -> float:
        """Latencia promedio por turno"""
        total = self.turns_completed + self.turns_failed
        return self.total_latency_ms / max(total, 1)
    
    @property
    def efficiency(self) -> float:
        """Eficiencia: tokens/ms"""
        return self.total_tokens_out / max(self.total_latency_ms, 1)


@dataclass
class DebateSessionBase:
    """Datos base de una sesión de debate"""
    id: str
    topic: str
    status: DebateStatus = DebateStatus.CREATED
    agents: List[AgentConfig] = field(default_factory=list)
    metrics: DebateMetrics = field(default_factory=DebateMetrics)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    transcript_path: Optional[str] = None
    final_summary: Optional[str] = None
    error_message: Optional[str] = None


# ============================================================================
# PROTOCOLO DE EVENTOS
# ============================================================================

class EventCallback(Protocol):
    """Protocolo para callbacks de eventos de debate"""
    async def __call__(self, event_type: str, data: Dict[str, Any]) -> None:
        ...


# ============================================================================
# BASE CONTROLLER
# ============================================================================

class BaseDebateController(ABC):
    """
    Controlador base para todos los tipos de debate.
    
    Responsabilidades:
    - Gestión del ciclo de vida del debate (crear, iniciar, finalizar)
    - Logging estructurado consistente
    - Métricas comunes (tokens, latencia)
    - Gestión de callbacks de eventos
    - Persistencia base de transcripts
    - Manejo de errores uniforme
    
    Las subclases deben implementar:
    - _execute_debate(): Lógica específica del tipo de debate
    - _create_debate_record(): Creación del registro en DB específico
    """
    
    # Directorio base para transcripts
    TRANSCRIPTS_DIR = os.path.join(
        os.path.dirname(__file__), '..', '..', 'data', 'debates'
    )
    
    def __init__(self, controller_name: str):
        """
        Inicializa el controlador base.
        
        Args:
            controller_name: Identificador del tipo de controlador
        """
        self.controller_name = controller_name
        self.logger = logger.bind(controller=controller_name)
        
        # Asegurar directorio de transcripts existe
        os.makedirs(self.TRANSCRIPTS_DIR, exist_ok=True)
    
    # -------------------------------------------------------------------------
    # MÉTODOS PÚBLICOS (API)
    # -------------------------------------------------------------------------
    
    async def create_debate(
        self,
        topic: str,
        agents_config: List[AgentConfig],
        max_rounds: int = 3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DebateSessionBase:
        """
        Crea una nueva sesión de debate.
        
        Args:
            topic: Tema del debate
            agents_config: Lista de configuraciones de agentes
            max_rounds: Número máximo de rondas/turnos
            metadata: Metadatos adicionales
            
        Returns:
            DebateSessionBase con el debate creado
        """
        session_id = str(uuid.uuid4())
        
        # Crear path de transcript
        transcript_filename = f"{self.controller_name}_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        transcript_path = os.path.join(self.TRANSCRIPTS_DIR, transcript_filename)
        
        session = DebateSessionBase(
            id=session_id,
            topic=topic,
            status=DebateStatus.CREATED,
            agents=agents_config,
            transcript_path=transcript_path,
            created_at=datetime.now()
        )
        
        # Crear archivo de transcript vacío
        await self._initialize_transcript(session, metadata or {})
        
        self.logger.info(
            "debate.created",
            session_id=session_id,
            topic=topic[:100],
            agents=len(agents_config),
            max_rounds=max_rounds
        )
        
        return session
    
    async def run_debate(
        self,
        session: DebateSessionBase,
        db_session: Optional[AsyncSession] = None,
        on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> DebateSessionBase:
        """
        Ejecuta un debate completo.
        
        Args:
            session: Sesión a ejecutar (creada con create_debate)
            db_session: Sesión de base de datos (opcional)
            on_event: Callback para eventos de progreso
            
        Returns:
            DebateSessionBase actualizado con resultados
        """
        session.status = DebateStatus.RUNNING
        
        self.logger.info(
            "debate.started",
            session_id=session.id,
            topic=session.topic[:100]
        )
        
        if on_event:
            await self._emit_event(on_event, "debate_started", {
                "session_id": session.id,
                "topic": session.topic,
                "agents": [a.id for a in session.agents]
            })
        
        try:
            # Ejecutar lógica específica (implementada por subclase)
            await self._execute_debate(session, db_session, on_event)
            
            # Finalización exitosa
            if session.status not in [DebateStatus.FAILED, DebateStatus.CONSENSUS_FAILED]:
                session.status = DebateStatus.COMPLETED
            
            session.completed_at = datetime.now()
            
            self.logger.info(
                "debate.completed",
                session_id=session.id,
                status=session.status.value,
                duration_ms=self._calculate_duration(session),
                tokens_in=session.metrics.total_tokens_in,
                tokens_out=session.metrics.total_tokens_out,
                avg_latency_ms=session.metrics.avg_latency_ms
            )
            
            if on_event:
                await self._emit_event(on_event, "debate_completed", {
                    "session_id": session.id,
                    "status": session.status.value,
                    "metrics": {
                        "tokens_in": session.metrics.total_tokens_in,
                        "tokens_out": session.metrics.total_tokens_out,
                        "avg_latency_ms": session.metrics.avg_latency_ms,
                        "duration_ms": self._calculate_duration(session)
                    }
                })
            
        except Exception as e:
            session.status = DebateStatus.FAILED
            session.error_message = str(e)
            session.completed_at = datetime.now()
            
            self.logger.error(
                "debate.failed",
                session_id=session.id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            if on_event:
                await self._emit_event(on_event, "debate_failed", {
                    "session_id": session.id,
                    "error": str(e)
                })
            
            # Re-lanzar para que el llamador pueda manejar
            raise
        
        finally:
            # Siempre guardar transcript final
            await self._finalize_transcript(session)
        
        return session
    
    # -------------------------------------------------------------------------
    # MÉTODOS ABSTRACTOS (subclases deben implementar)
    # -------------------------------------------------------------------------
    
    @abstractmethod
    async def _execute_debate(
        self,
        session: DebateSessionBase,
        db_session: Optional[AsyncSession],
        on_event: Optional[Callable[[str, Dict[str, Any]], None]]
    ) -> None:
        """
        Lógica específica de ejecución del debate.
        
        Las subclases deben implementar su flujo de debate aquí.
        Deben actualizar session.metrics y session.status según el progreso.
        """
        pass
    
    @abstractmethod
    async def _create_debate_record(
        self,
        session: DebateSessionBase,
        db_session: AsyncSession
    ) -> Any:
        """
        Crea el registro específico en la base de datos.
        
        Returns:
            El objeto de modelo ORM creado
        """
        pass
    
    # -------------------------------------------------------------------------
    # MÉTODOS DE UTILIDAD (helpers para subclases)
    # -------------------------------------------------------------------------
    
    async def _emit_event(
        self,
        callback: Optional[Callable[[str, Dict[str, Any]], None]],
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Emite un evento al callback si está disponible.
        Maneja excepciones silenciosamente para no interrumpir el debate.
        """
        if callback is None:
            return
        
        try:
            # Soportar tanto callbacks sync como async
            if asyncio.iscoroutinefunction(callback):
                await callback(event_type, data)
            else:
                callback(event_type, data)
        except Exception as e:
            self.logger.warning(
                "debate.event_callback_failed",
                event_type=event_type,
                error=str(e)
            )
    
    def _calculate_duration(self, session: DebateSessionBase) -> int:
        """Calcula duración del debate en ms"""
        if session.completed_at and session.created_at:
            delta = session.completed_at - session.created_at
            return int(delta.total_seconds() * 1000)
        return 0
    
    async def _initialize_transcript(
        self,
        session: DebateSessionBase,
        metadata: Dict[str, Any]
    ) -> None:
        """Inicializa archivo de transcript"""
        if session.transcript_path is None:
            return
        
        transcript = {
            "version": "2.0",
            "controller": self.controller_name,
            "session_id": session.id,
            "topic": session.topic,
            "created_at": session.created_at.isoformat(),
            "metadata": metadata,
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "role": a.role.value,
                    "model": a.model,
                    "engine": a.engine,
                    "node": a.node
                }
                for a in session.agents
            ],
            "turns": []
        }
        
        await self._write_transcript(session.transcript_path, transcript)
    
    async def _append_turn_to_transcript(
        self,
        session: DebateSessionBase,
        turn_data: Dict[str, Any]
    ) -> None:
        """Añade un turno al transcript existente"""
        if session.transcript_path is None:
            return
        
        try:
            # Leer transcript existente
            transcript = await self._read_transcript(session.transcript_path)
            
            # Añadir turno
            turn_data["timestamp"] = datetime.now().isoformat()
            transcript["turns"].append(turn_data)
            
            # Actualizar métricas
            transcript["metrics"] = {
                "total_tokens_in": session.metrics.total_tokens_in,
                "total_tokens_out": session.metrics.total_tokens_out,
                "total_latency_ms": session.metrics.total_latency_ms,
                "turns_completed": session.metrics.turns_completed
            }
            
            await self._write_transcript(session.transcript_path, transcript)
            
        except Exception as e:
            self.logger.warning(
                "debate.transcript_append_failed",
                session_id=session.id,
                error=str(e)
            )
    
    async def _finalize_transcript(self, session: DebateSessionBase) -> None:
        """Finaliza transcript con datos de cierre"""
        if session.transcript_path is None:
            return
        
        try:
            transcript = await self._read_transcript(session.transcript_path)
            
            transcript.update({
                "status": session.status.value,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "duration_ms": self._calculate_duration(session),
                "final_summary": session.final_summary,
                "final_metrics": {
                    "total_tokens_in": session.metrics.total_tokens_in,
                    "total_tokens_out": session.metrics.total_tokens_out,
                    "total_latency_ms": session.metrics.total_latency_ms,
                    "avg_latency_ms": session.metrics.avg_latency_ms,
                    "turns_completed": session.metrics.turns_completed,
                    "turns_failed": session.metrics.turns_failed
                }
            })
            
            await self._write_transcript(session.transcript_path, transcript)
            
        except Exception as e:
            self.logger.warning(
                "debate.transcript_finalize_failed",
                session_id=session.id,
                error=str(e)
            )
    
    async def _read_transcript(self, path: str) -> Dict[str, Any]:
        """Lee transcript desde archivo"""
        import aiofiles
        async with aiofiles.open(path, 'r', encoding='utf-8') as f:
            content = await f.read()
            import json
            return json.loads(content)
    
    async def _write_transcript(self, path: str, data: Dict[str, Any]) -> None:
        """Escribe transcript a archivo"""
        import aiofiles
        import json
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    
    async def get_db_session(self) -> AsyncSession:
        """Obtiene una sesión de base de datos"""
        return AsyncSessionLocal()
    
    def log_turn_start(
        self,
        session_id: str,
        turn_number: int,
        agent_id: str,
        agent_name: str
    ) -> None:
        """Log estándar de inicio de turno"""
        self.logger.info(
            "debate.turn_start",
            session_id=session_id,
            turn=turn_number,
            agent=agent_id,
            agent_name=agent_name
        )
    
    def log_turn_complete(
        self,
        session_id: str,
        turn_number: int,
        agent_id: str,
        tokens_out: int,
        latency_ms: int,
        status: str = "completed"
    ) -> None:
        """Log estándar de finalización de turno"""
        self.logger.info(
            "debate.turn_complete",
            session_id=session_id,
            turn=turn_number,
            agent=agent_id,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            status=status
        )
    
    def update_metrics(
        self,
        session: DebateSessionBase,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: int = 0,
        success: bool = True
    ) -> None:
        """Actualiza métricas de sesión"""
        session.metrics.total_tokens_in += tokens_in
        session.metrics.total_tokens_out += tokens_out
        session.metrics.total_latency_ms += latency_ms
        
        if success:
            session.metrics.turns_completed += 1
        else:
            session.metrics.turns_failed += 1


# ============================================================================
# EXCEPCIONES ESPECÍFICAS
# ============================================================================

class DebateControllerError(Exception):
    """Error base para controladores de debate"""
    pass


class AgentExecutionError(DebateControllerError):
    """Error en la ejecución de un agente"""
    
    def __init__(self, agent_id: str, message: str, original_error: Optional[Exception] = None):
        self.agent_id = agent_id
        self.original_error = original_error
        super().__init__(f"Agent {agent_id}: {message}")


class ConvergenceError(DebateControllerError):
    """Error en el proceso de convergencia/consenso"""
    pass


class TribunalError(DebateControllerError):
    """Error en la ejecución del tribunal"""
    pass
