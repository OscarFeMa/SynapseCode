"""
Synapse Council v2.0 - Database Models
SQLAlchemy 2.x models para SQLite local (Scratchpad)

Tablas:
- sessions: Registro maestro de debates
- rounds: Una fila por ronda de debate
- agent_calls: Registro granular de llamadas a agentes
- cross_references: Grafo de dependencias entre agentes
- agent_reputation: Sistema de reputación por méritos con EMA
- config_profiles: Perfiles de configuración guardados
- system_events: Log de eventos del sistema
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    String, Integer, Float, Text, Boolean, ForeignKey, DateTime, 
    Index, JSON, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos"""
    pass


def generate_uuid() -> str:
    """Genera UUID v4 como string"""
    return str(uuid.uuid4())


class Session(Base):
    """
    Tabla: sessions
    Registro maestro de cada debate
    """
    __tablename__ = "sessions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="CREATED"
    )  # CREATED|RUNNING|COMPLETED|FAILED|CONSENSUS_NOT_REACHED
    consensus_level: Mapped[Optional[str]] = mapped_column(
        String(30), 
        nullable=True
    )  # CONSENSUS_REACHED|PARTIAL_CONSENSUS|DIVERGENT
    rounds_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    final_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tribunal_verdict: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    node_origin: Mapped[str] = mapped_column(
        String(10), 
        nullable=False, 
        default="MASTER"
    )  # MASTER|WORKER
    total_tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    elevated_to_cloud: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    elevation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    
    # Relaciones
    rounds: Mapped[List["Round"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    agent_calls: Mapped[List["AgentCall"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_created_at", "created_at"),
        Index("idx_sessions_elevated", "elevated_to_cloud"),
    )


class Round(Base):
    """
    Tabla: rounds
    Una fila por ronda de debate
    """
    __tablename__ = "rounds"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # RUNNING|COMPLETED|FAILED
    convergence_status: Mapped[Optional[str]] = mapped_column(
        String(30), 
        nullable=True
    )  # CONSENSUS_REACHED|PARTIAL_CONSENSUS|DIVERGENT
    convergence_detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    session: Mapped["Session"] = relationship(back_populates="rounds")
    agent_calls: Mapped[List["AgentCall"]] = relationship(back_populates="round", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("session_id", "round_number", name="uix_round_session_number"),
        Index("idx_rounds_session_id", "session_id"),
    )


class AgentCall(Base):
    """
    Tabla: agent_calls
    Registro granular de cada llamada individual a un agente
    """
    __tablename__ = "agent_calls"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    round_id: Mapped[str] = mapped_column(ForeignKey("rounds.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # ANALYSIS|CRITIQUE|NODE_SYNTHESIS|META_SYNTHESIS|TRIBUNAL
    agent_slot: Mapped[str] = mapped_column(String(50), nullable=False)
    node: Mapped[str] = mapped_column(
        String(10), 
        nullable=False
    )  # LOCAL|CLOUD|WEB_AGENT
    engine: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # ollama|lm_studio|jan|openrouter|web_agent
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role_label: Mapped[str] = mapped_column(String(100), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(15), 
        nullable=False,
        default="PENDING"
    )  # PENDING|STREAMING|COMPLETED|FAILED|TIMEOUT|SKIPPED
    tokens_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    intervention_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    keep_alive_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reputation_impact: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    session: Mapped["Session"] = relationship(back_populates="agent_calls")
    round: Mapped["Round"] = relationship(back_populates="agent_calls")
    
    __table_args__ = (
        Index("idx_agent_calls_session_id", "session_id"),
        Index("idx_agent_calls_round_id", "round_id"),
        Index("idx_agent_calls_phase", "phase"),
        Index("idx_agent_calls_engine", "engine"),
        Index("idx_agent_calls_status", "status"),
    )


class CrossReference(Base):
    """
    Tabla: cross_references
    Grafo de dependencias entre agentes
    """
    __tablename__ = "cross_references"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    consumer_call_id: Mapped[str] = mapped_column(ForeignKey("agent_calls.id"), nullable=False)
    source_call_id: Mapped[str] = mapped_column(ForeignKey("agent_calls.id"), nullable=False)
    context_type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # ANALYSIS_INPUT|CRITIQUE_INPUT|SYNTHESIS_INPUT|VERDICT_INPUT
    
    __table_args__ = (
        Index("idx_cross_ref_consumer", "consumer_call_id"),
        Index("idx_cross_ref_source", "source_call_id"),
    )


class AgentReputation(Base):
    """
    Tabla: agent_reputation (NUEVA v2.0)
    Sistema de reputación por méritos con EMA
    """
    __tablename__ = "agent_reputation"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    agent_slot: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    engine: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # ollama|lm_studio|jan|openrouter|web_agent
    domain: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # technical|strategy|security|creative|general
    reputation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    argument_survival_rate: Mapped[Optional[float]] = mapped_column(
        Float, 
        nullable=True, 
        default=0.0
    )  # TSA
    dialectic_independence: Mapped[Optional[float]] = mapped_column(
        Float, 
        nullable=True, 
        default=0.5
    )  # IID
    technical_precision: Mapped[Optional[float]] = mapped_column(
        Float, 
        nullable=True, 
        default=0.5
    )  # PVT
    total_debates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    
    __table_args__ = (
        UniqueConstraint(
            "agent_slot", "model_name", "domain", 
            name="uix_agent_reputation"
        ),
        Index("idx_agent_reputation_score", "reputation_score"),
        Index("idx_agent_reputation_domain", "domain"),
    )


class ConfigProfile(Base):
    """
    Tabla: config_profiles
    Perfiles de configuración guardados
    """
    __tablename__ = "config_profiles"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )


class SequentialDebate(Base):
    """
    Tabla: sequential_debates
    Registro de debates secuenciales multi-modelo
    """
    __tablename__ = "sequential_debates"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="created"
    )  # created|running|completed|failed
    total_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    final_verdict: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_report: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    transcript_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    turns: Mapped[List["SequentialDebateTurn"]] = relationship(
        "SequentialDebateTurn",
        back_populates="debate",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_sequential_debate_status", "status"),
        Index("idx_sequential_debate_created", "created_at"),
    )


class SequentialDebateTurn(Base):
    """
    Tabla: sequential_debate_turns
    Registro de cada turno en un debate secuencial
    """
    __tablename__ = "sequential_debate_turns"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    debate_id: Mapped[str] = mapped_column(
        ForeignKey("sequential_debates.id"),
        nullable=False
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    node: Mapped[str] = mapped_column(String(10), nullable=False)  # LOCAL|CLOUD
    engine: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Prompt y respuesta
    prompt_sent: Mapped[str] = mapped_column(Text, nullable=False)
    response_received: Mapped[str] = mapped_column(Text, nullable=False, default="")
    
    # Métricas
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Estado
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="pending"
    )  # pending|running|completed|failed|completed (fallback)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    debate: Mapped["SequentialDebate"] = relationship(
        "SequentialDebate",
        back_populates="turns"
    )
    
    __table_args__ = (
        Index("idx_debate_turn_debate_id", "debate_id"),
        Index("idx_debate_turn_number", "debate_id", "turn_number"),
        Index("idx_debate_turn_status", "status"),
    )


class SystemEvent(Base):
    """
    Tabla: system_events
    Log de eventos del sistema
    """
    __tablename__ = "system_events"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sessions.id"), 
        nullable=True
    )
    debate_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sequential_debates.id"),
        nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(10), 
        nullable=False
    )  # INFO|WARNING|ERROR|CRITICAL
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    
    __table_args__ = (
        Index("idx_system_events_session", "session_id"),
        Index("idx_system_events_debate", "debate_id"),
        Index("idx_system_events_type", "event_type"),
    )


# ============================================================================
# Consensus Debate Models - Sistema de Consenso Multi-Modelo
# ============================================================================

class ConsensusDebate(Base):
    """Registro maestro de debate de consenso"""
    __tablename__ = "consensus_debates"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running"
    )  # running, consensus_reached, partial_consensus, max_rounds_reached, failed
    
    # Configuración
    total_agents: Mapped[int] = mapped_column(Integer, default=0)
    max_rounds: Mapped[int] = mapped_column(Integer, default=5)
    
    # Métricas de consenso
    consensus_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )  # 0-1 score final
    
    # Resultados
    final_consensus: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bias_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Transcripción
    transcript_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Métricas
    total_tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    rounds: Mapped[List["ConsensusRound"]] = relationship(
        "ConsensusRound",
        back_populates="debate",
        cascade="all, delete-orphan"
    )
    agent_positions: Mapped[List["ConsensusAgentPosition"]] = relationship(
        "ConsensusAgentPosition",
        back_populates="debate",
        cascade="all, delete-orphan"
    )


class ConsensusRound(Base):
    """Ronda individual en un debate de consenso"""
    __tablename__ = "consensus_rounds"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    debate_id: Mapped[str] = mapped_column(
        ForeignKey("consensus_debates.id"),
        nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    round_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # proposal, refutation, synthesis, validation, convergence
    
    # Métricas de la ronda
    global_consensus_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    converged: Mapped[bool] = mapped_column(Boolean, default=False)
    dissent_topics: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    # Relaciones
    debate: Mapped["ConsensusDebate"] = relationship("ConsensusDebate", back_populates="rounds")
    agent_positions: Mapped[List["ConsensusAgentPosition"]] = relationship(
        "ConsensusAgentPosition",
        back_populates="round",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_consensus_rounds_debate", "debate_id", "round_number"),
    )


class ConsensusAgentPosition(Base):
    """Posición de un agente en una ronda de consenso"""
    __tablename__ = "consensus_agent_positions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    debate_id: Mapped[str] = mapped_column(
        ForeignKey("consensus_debates.id"),
        nullable=False
    )
    round_id: Mapped[int] = mapped_column(
        ForeignKey("consensus_rounds.id"),
        nullable=False
    )
    
    # Info del agente
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Posición
    position_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    consensus_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    
    # Datos estructurados
    supporting_points: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    objections_raised: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    logical_fallacies: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    # Relaciones
    debate: Mapped["ConsensusDebate"] = relationship("ConsensusDebate", back_populates="agent_positions")
    round: Mapped["ConsensusRound"] = relationship("ConsensusRound", back_populates="agent_positions")
    
    __table_args__ = (
        Index("idx_consensus_positions_debate", "debate_id"),
        Index("idx_consensus_positions_agent", "agent_id"),
        Index("idx_consensus_positions_round", "round_id"),
    )


class ModelReputation(Base):
    """
    Sistema de reputación EMA para modelos.
    Scores por modelo y rol: TSA, IID, PVT, Efficiency.
    """
    __tablename__ = 'model_reputation'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default='unknown')
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    
    # Scores EMA (Exponential Moving Average)
    tsa_score: Mapped[float] = mapped_column(Float, default=0.5)  # Tasa de Supervivencia de Argumentos
    iid_score: Mapped[float] = mapped_column(Float, default=0.5)  # Índice de Independencia Dialéctica
    pvt_score: Mapped[float] = mapped_column(Float, default=0.5)  # Puntuación de Verificación Técnica
    efficiency_score: Mapped[float] = mapped_column(Float, default=0.5)  # Eficiencia (tokens/ms)
    
    # Score compuesto
    reputation_score: Mapped[float] = mapped_column(Float, default=0.5)
    
    # Estadísticas
    total_debates: Mapped[int] = mapped_column(Integer, default=0)
    total_turns: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraint único por modelo+rol
    __table_args__ = (
        UniqueConstraint('model', 'role', name='uq_model_role'),
        Index('idx_reputation_score', 'reputation_score'),
        Index('idx_reputation_model', 'model'),
    )
    
    def __repr__(self):
        return f"<ModelReputation {self.model}@{self.role}={self.reputation_score:.2f}>"
