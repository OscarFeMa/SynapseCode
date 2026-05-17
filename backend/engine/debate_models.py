from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentRole(Enum):
    """Roles disponibles para agentes en el debate"""

    ANALYST = "analyst"  # Analiza el tema propuesto
    CRITIC = "critic"  # Critica el análisis anterior
    SYNTHESIZER = "synthesizer"  # Síntesis de argumentos
    REFINER = "refiner"  # Refina conclusiones
    MODERATOR = "moderator"  # Moderador/veredicto final
    VALIDATOR = "validator"  # Valida argumentos y evidencia
    CONSENSUS = "consensus"  # Busca puntos de acuerdo
    TRIBUNAL = "tribunal"  # Magistrado del tribunal


@dataclass
class DebateAgent:
    """Configuración de un agente en el debate"""

    id: str
    name: str
    role: AgentRole
    node: str  # LOCAL, CLOUD
    engine: str  # ollama, openrouter, groq, gemini, etc
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
class CruzamientoCritico:
    """Representa una respuesta crítica entre dos agentes"""

    from_agent: str  # Agente que responde
    to_agent: str  # Agente al que se responde
    target_argument: str  # Argumento específico que se critica/valida
    response: str  # Respuesta crítica
    iteration: int  # Número de iteración
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IteracionDebate:
    """Una iteración completa del debate con múltiples fases"""

    iteration_number: int
    phase: str  # analysis, criticism, validation, consensus
    turns: List[DebateTurn] = field(default_factory=list)
    cruzamientos: List[CruzamientoCritico] = field(default_factory=list)
    consensus_points: List[str] = field(default_factory=list)
    disagreement_points: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def get_context_summary(self) -> str:
        summary = []
        for turn in self.turns:
            summary.append(f"{turn.agent.name} ({turn.agent.role.value}): {turn.response_received[:200]}...")
        return "\n\n".join(summary)


@dataclass
class DebateSession:
    """Sesión completa de debate con soporte para iteraciones"""

    id: str
    topic: str
    turns: List[DebateTurn] = field(default_factory=list)
    iterations: List[IteracionDebate] = field(default_factory=list)
    context_history: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "created"  # created, running, paused, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    pause_reason: Optional[str] = None
    final_verdict: Optional[str] = None

    # Campos para Tribunal y Convergence (v2.1)
    tribunal_verdict: Optional[Dict[str, Any]] = None
    consensus_score: float = 0.0
    convergence_level: str = "UNKNOWN"
    structured_report: Optional[Dict[str, Any]] = None
    web_context: Optional[Dict[str, Any]] = None  # Contexto de búsqueda web

    # Configuración de iteraciones
    current_iteration: int = 0
    max_iterations: int = 3
    consensus_reached: bool = False

    def get_iteration_context(self, iteration_num: int) -> str:
        """Obtiene el contexto acumulado hasta una iteración específica"""
        context_parts = []
        for i, iteration in enumerate(self.iterations[:iteration_num], 1):
            context_parts.append(f"=== ITERACIÓN {i} ({iteration.phase}) ===")
            context_parts.append(iteration.get_context_summary())
            if iteration.cruzamientos:
                context_parts.append("--- Cruzamientos Críticos ---")
                for cruz in iteration.cruzamientos:
                    context_parts.append(f"{cruz.from_agent} → {cruz.to_agent}: {cruz.response[:150]}...")
        return "\n\n".join(context_parts)

    def build_context_prompt(self, current_agent: DebateAgent) -> str:
        """Construye el prompt con todo el contexto acumulado"""
        import structlog

        from backend.engine.quality_monitor import is_response_usable

        logger = structlog.get_logger()

        lines = [
            f"# DEBATE SECUENCIAL: {self.topic}",
            "",
            "## Tu Rol",
            f"Eres: {current_agent.name}",
            f"Rol: {current_agent.role.value}",
            f"Modelo: {current_agent.model} ({current_agent.provider})",
            "",
        ]

        # Inyectar contexto web si existe
        if self.web_context:
            from backend.engine.web_search_service import WebContext

            web_ctx = WebContext.from_dict(self.web_context)
            if web_ctx.searches:
                lines.append("## Información Actualizada (Búsqueda Web)")
                lines.append("Los siguientes resultados provienen de búsquedas web en tiempo real sobre el tema.")
                lines.append("Úsalos como contexto adicional pero mantén tu pensamiento crítico.")
                lines.append("")
                for result in web_ctx.searches:
                    if result.success:
                        lines.append(f"### {result.site_label}")
                        lines.append(result.response[:2000])
                        lines.append("")

        lines.append("## Historial del Debate")

        for turn in self.turns:
            if turn.status.startswith("completed"):
                # Filtro de calidad (v2.1)
                if not is_response_usable(turn.response_received, turn.agent.role.value):
                    logger.warning(
                        "sequential_debate.omitting_low_quality_turn",
                        turn=turn.turn_number,
                        agent=turn.agent.name,
                    )
                    continue

                lines.append(f"\n### Turno {turn.turn_number}: {turn.agent.name} ({turn.agent.role.value})")
                lines.append(f"**Modelo:** {turn.agent.model} ({turn.agent.provider})")
                lines.append(f"\n{turn.response_received}")

        lines.append("\n" + "=" * 60)
        lines.append("\n## Tu Tarea")

        return "\n".join(lines)
