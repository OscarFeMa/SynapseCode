from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentRole(Enum):
    """Roles disponibles para agentes en el debate"""

    ANALYST = "analyst"  # Analiza el tema propuesto
    CRITIC = "critic"  # Critica el analisis anterior
    SYNTHESIZER = "synthesizer"  # Sintesis de argumentos
    REFINER = "refiner"  # Refina conclusiones
    MODERATOR = "moderator"  # Moderador/veredicto final
    VALIDATOR = "validator"  # Valida argumentos y evidencia
    CONSENSUS = "consensus"  # Busca puntos de acuerdo
    TRIBUNAL = "tribunal"  # Magistrado del tribunal


# Constantes para sliding window
SLIDING_WINDOW_KEEP_RECENT = 2  # Iteraciones recientes en detalle
SLIDING_WINDOW_SUMMARY_CHARS = 500  # Max chars por iteracion resumida


@dataclass
class DebateAgent:
    """Configuracion de un agente en el debate"""

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
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "pending"  # pending, running, completed, failed


@dataclass
class CruzamientoCritico:
    """Representa una respuesta critica entre dos agentes"""

    from_agent: str  # Agente que responde
    to_agent: str  # Agente al que se responde
    target_argument: str  # Argumento especifico que se critica/valida
    response: str  # Respuesta critica
    iteration: int  # Numero de iteracion
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IteracionDebate:
    """Una iteracion completa del debate con multiples fases"""

    iteration_number: int
    phase: str  # analysis, criticism, validation, consensus
    turns: list[DebateTurn] = field(default_factory=list)
    cruzamientos: list[CruzamientoCritico] = field(default_factory=list)
    consensus_points: list[str] = field(default_factory=list)
    disagreement_points: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def get_context_summary(self) -> str:
        summary = []
        for turn in self.turns:
            summary.append(f"{turn.agent.name} ({turn.agent.role.value}): {turn.response_received[:200]}...")
        return "\n\n".join(summary)

    def get_compact_summary(self, max_chars: int = SLIDING_WINDOW_SUMMARY_CHARS) -> str:
        """Version compacta para sliding window"""
        parts = []
        for turn in self.turns:
            agent_info = f"{turn.agent.name} ({turn.agent.role.value})"
            # Extraer puntos clave (primeras 2-3 oraciones)
            text = turn.response_received.strip()
            sentences = text.replace(". ", ".\n").split("\n")[:3]
            key_points = " ".join(s.strip() for s in sentences if s.strip())
            if key_points:
                parts.append(f"- {agent_info}: {key_points[:150]}")
            else:
                parts.append(f"- {agent_info}: [sin respuesta]")

        summary = " | ".join(parts)
        return summary[:max_chars] + ("..." if len(summary) > max_chars else "")


@dataclass
class DebateSession:
    """Sesion completa de debate con soporte para iteraciones"""

    id: str
    topic: str
    turns: list[DebateTurn] = field(default_factory=list)
    iterations: list[IteracionDebate] = field(default_factory=list)
    context_history: list[dict[str, Any]] = field(default_factory=list)
    status: str = "created"  # created, running, paused, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    paused_at: datetime | None = None
    pause_reason: str | None = None
    final_verdict: str | None = None

    # Campos para Tribunal y Convergence (v2.1)
    tribunal_verdict: dict[str, Any] | None = None
    consensus_score: float = 0.0
    convergence_level: str = "UNKNOWN"
    structured_report: dict[str, Any] | None = None
    web_context: dict[str, Any] | None = None  # Contexto de busqueda web

    # Configuracion de iteraciones
    current_iteration: int = 0
    max_iterations: int = 3
    consensus_reached: bool = False

    # Sliding window config
    enable_sliding_window: bool = True

    def get_iteration_context(self, iteration_num: int) -> str:
        """Obtiene el contexto acumulado hasta una iteracion especifica"""
        if not self.enable_sliding_window:
            return self._get_full_context(iteration_num)
        return self._get_sliding_window_context(iteration_num)

    def _get_full_context(self, iteration_num: int) -> str:
        """Contexto completo sin sliding window (legacy)"""
        context_parts = []
        for i, iteration in enumerate(self.iterations[:iteration_num], 1):
            context_parts.append(f"=== ITERACION {i} ({iteration.phase}) ===")
            context_parts.append(iteration.get_context_summary())
            if iteration.cruzamientos:
                context_parts.append("--- Cruzamientos Criticos ---")
                for cruz in iteration.cruzamientos:
                    context_parts.append(f"{cruz.from_agent} -> {cruz.to_agent}: {cruz.response[:150]}...")
        return "\n\n".join(context_parts)

    def _get_sliding_window_context(self, iteration_num: int) -> str:
        """Contexto con sliding window: iteraciones recientes en detalle, antiguas resumidas"""
        total_iterations = len(self.iterations[:iteration_num])

        if total_iterations <= SLIDING_WINDOW_KEEP_RECENT:
            # Todas caben en la ventana, usar contexto completo
            return self._get_full_context(iteration_num)

        context_parts = []

        # Iteraciones antiguas: resumen compacto
        old_count = total_iterations - SLIDING_WINDOW_KEEP_RECENT
        context_parts.append(f"=== RESUMEN DE {old_count} ITERACIONES ANTERIORES (contexto comprimido) ===")

        for i, iteration in enumerate(self.iterations[:old_count], 1):
            summary = iteration.get_compact_summary()
            context_parts.append(f"[Iter {i} - {iteration.phase}] {summary}")

        # Agregar puntos de consenso/desacuerdo acumulados
        all_consensus = []
        all_disagreement = []
        for iteration in self.iterations[:old_count]:
            all_consensus.extend(iteration.consensus_points[:2])
            all_disagreement.extend(iteration.disagreement_points[:2])

        if all_consensus:
            context_parts.append("\nPuntos de consenso alcanzados:")
            for point in all_consensus[:5]:
                context_parts.append(f"  - {point[:100]}")

        if all_disagreement:
            context_parts.append("\nPuntos de desacuerdo pendientes:")
            for point in all_disagreement[:5]:
                context_parts.append(f"  - {point[:100]}")

        # Iteraciones recientes: contexto completo
        context_parts.append("\n=== ITERACIONES RECIENTES (detalle completo) ===")
        for i, iteration in enumerate(self.iterations[old_count:iteration_num], old_count + 1):
            context_parts.append(f"\n=== ITERACION {i} ({iteration.phase}) ===")
            context_parts.append(iteration.get_context_summary())
            if iteration.cruzamientos:
                context_parts.append("--- Cruzamientos Criticos ---")
                for cruz in iteration.cruzamientos:
                    context_parts.append(f"{cruz.from_agent} -> {cruz.to_agent}: {cruz.response[:150]}...")

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
                lines.append("## Informacion Actualizada (Busqueda Web)")
                lines.append("Los siguientes resultados provienen de busquedas web en tiempo real sobre el tema.")
                lines.append("Usalos como contexto adicional pero manteni tu pensamiento critico.")
                lines.append("")
                for result in web_ctx.searches:
                    if result.success:
                        lines.append(f"### {result.site_label}")
                        lines.append(result.response[:2000])
                        lines.append("")

        lines.append("## Historial del Debate")

        if self.enable_sliding_window and len(self.turns) > 10:
            # Aplicar sliding window a turns tambien
            recent_turns = self.turns[-10:]
            old_turns = self.turns[:-10]

            if old_turns:
                lines.append(f"\n### Resumen de {len(old_turns)} turnos anteriores")
                old_summary_parts = []
                for turn in old_turns:
                    if turn.status.startswith("completed"):
                        # Extraer idea principal
                        text = turn.response_received.strip()
                        first_sentence = text.split(".")[0][:100]
                        old_summary_parts.append(f"- {turn.agent.name}: {first_sentence}")
                lines.append("\n".join(old_summary_parts))

            lines.append("\n### Turnos recientes (detalle completo)")
            for turn in recent_turns:
                if turn.status.startswith("completed"):
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
        else:
            for turn in self.turns:
                if turn.status.startswith("completed"):
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
