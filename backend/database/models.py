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
from datetime import datetime, UTC
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


def utc_now() -> datetime:
    """Genera timestamps timezone-aware en UTC para defaults de SQLAlchemy."""
    return datetime.now(UTC)


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
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=utc_now
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
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
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
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
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
        default=utc_now
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
        default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=utc_now
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
        default=utc_now
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


class ReductioAbsurdumProof(Base):
    """
    Tabla: reductio_absurdum_proofs
    Persistencia de desafíos y pruebas de reducción al absurdo por debate.
    """
    __tablename__ = "reductio_absurdum_proofs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    debate_id: Mapped[str] = mapped_column(
        ForeignKey("sequential_debates.id"),
        nullable=False
    )
    iteration_number: Mapped[int] = mapped_column(Integer, nullable=False)

    proposition: Mapped[str] = mapped_column(Text, nullable=False)
    extreme_case: Mapped[str] = mapped_column(Text, nullable=False)
    contradiction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    questioning_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    challenged_agent: Mapped[str] = mapped_column(String(100), nullable=False)

    consensus_areas: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    weak_assumptions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    unquestioned_premises: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    overall_complacency_risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recommendations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now
    )

    __table_args__ = (
        Index("idx_reductio_debate_iteration", "debate_id", "iteration_number"),
        Index("idx_reductio_questioning_agent", "questioning_agent"),
        Index("idx_reductio_challenged_agent", "challenged_agent"),
    )


class PromptResponseCache(Base):
    """
    Tabla: prompt_response_cache
    Caché semántica de respuestas por embedding + configuración.
    """
    __tablename__ = "prompt_response_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    engine: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    node: Mapped[str] = mapped_column(String(20), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_embedding: Mapped[Optional[bytes]] = mapped_column(Text, nullable=True)  # JSON array de floats
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    similarity_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_prompt_cache_engine_model", "engine", "model"),
        Index("idx_prompt_cache_last_accessed", "last_accessed_at"),
        Index("idx_prompt_cache_expires", "expires_at"),
    )


class SupabaseSyncQueueItem(Base):
    """
    Tabla: supabase_sync_queue
    Cola persistente para sincronización confiable con Supabase.
    """
    __tablename__ = "supabase_sync_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False, default="debate")
    debate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("idx_sync_queue_status_next_attempt", "status", "next_attempt_at"),
        Index("idx_sync_queue_debate_id", "debate_id"),
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
        default=utc_now
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
        default=utc_now
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
        default=utc_now
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
        default=utc_now
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Constraint único por modelo+rol
    __table_args__ = (
        UniqueConstraint('model', 'role', name='uq_model_role'),
        Index('idx_reputation_score', 'reputation_score'),
        Index('idx_reputation_model', 'model'),
    )
    
    def __repr__(self):
        return f"<ModelReputation {self.model}@{self.role}={self.reputation_score:.2f}>"


# ============================================================================
# Data Warehouse Models - Analytics & Historical Analysis
# ============================================================================

class DebateAggregate(Base):
    """
    Tabla: debates_aggregate
    Agregación principal por debate (unifica Session y SequentialDebate)
    """
    __tablename__ = "debates_aggregate"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    debate_type: Mapped[str] = mapped_column(String(20), nullable=False)  # session|sequential
    topic_text: Mapped[str] = mapped_column(Text, nullable=False)  # query o topic normalizado
    topic_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # hash para agrupación
    mode: Mapped[str] = mapped_column(String(30), nullable=False)  # standard|ultra_crossing|classic
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    consensus_level: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    rounds_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_tribunal_verdict: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_reductio_proofs: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unique_models_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("idx_debate_agg_type_status", "debate_type", "status"),
        Index("idx_debate_agg_created", "created_at"),
        Index("idx_debate_agg_topic_hash", "topic_hash"),
    )


class TopicTrending(Base):
    """
    Tabla: topics_trending
    Agregación diaria de temas más debatidos
    """
    __tablename__ = "topics_trending"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    topic_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    topic_text: Mapped[str] = mapped_column(Text, nullable=False)
    debate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_consensus_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unique_models_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("date", "topic_hash", name="uq_topic_trending_date_hash"),
        Index("idx_topic_trending_date_count", "date", "debate_count"),
        Index("idx_topic_trending_hash", "topic_hash"),
    )


class ConsensusPattern(Base):
    """
    Tabla: consensus_patterns
    Patrones de consenso por tema y configuración
    """
    __tablename__ = "consensus_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), nullable=False)
    consensus_level: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    debate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_rounds_to_convergence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_tokens_per_debate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("topic_hash", "mode", "consensus_level", name="uq_consensus_pattern"),
        Index("idx_consensus_pattern_topic_mode", "topic_hash", "mode"),
        Index("idx_consensus_pattern_level", "consensus_level"),
    )


class ModelPerformance(Base):
    """
    Tabla: model_performance
    Performance de modelos por rol
    """
    __tablename__ = "model_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    engine: Mapped[str] = mapped_column(String(20), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(30), nullable=False)
    total_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_tokens_out: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tsa_score_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    iid_score_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    pvt_score_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    efficiency_score_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("model_name", "agent_role", name="uq_model_performance"),
        Index("idx_model_perf_role", "model_name", "agent_role"),
        Index("idx_model_perf_efficiency", "efficiency_score_avg"),
    )


class DailyMetricsSnapshot(Base):
    """
    Tabla: daily_metrics_snapshot
    Snapshot diario de métricas globales
    """
    __tablename__ = "daily_metrics_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)  # YYYY-MM-DD
    total_debates_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_debates_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_turns_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_debate_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unique_topics_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_models_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        Index("idx_daily_metrics_date", "date"),
    )
