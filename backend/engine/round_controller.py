"""
Synapse Council v2.0 - Round Controller
Controla el flujo de una ronda de debate:
1. FASE 1: Análisis (4 analistas en paralelo)
2. FASE 2: Crítica (4 críticos con cruce híbrido)
3. FASE 3: Síntesis (2 nodos)
4. FASE 4: Tribunal (3 magistrados - Fase 2)
"""

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.models import Round
from backend.engine.agent_orchestrator import (
    AgentConfig,
    AgentOrchestrator,
    AgentResult,
)
from backend.engine.prompts import PromptBuilder
from backend.engine.tribunal import TribunalCouncil

settings = get_settings()
logger = structlog.get_logger()


class RoundController:
    """
    Controlador de ronda de debate.
    Gestiona las 4 fases con cruce híbrido Local↔Nube.
    """

    # Configuración de agentes por fase (modelos disponibles en Worker y Master)
    ANALYSIS_AGENTS = [
        # Todos a mistral:7b por estabilidad mientras el Worker está offline
        AgentConfig(
            "analyst_local_a",
            "LOCAL",
            "ollama",
            "mistral:7b",
            "Analista Técnico (Local)",
            max_tokens=1000,
        ),
        AgentConfig(
            "analyst_local_b",
            "LOCAL",
            "ollama",
            "mistral:7b",
            "Analista de Riesgos (Local)",
            max_tokens=1000,
        ),
        AgentConfig(
            "analyst_cloud_a",
            "CLOUD",
            "ollama",
            "llama3.2:latest",
            "Analista de Negocio (Master)",
            max_tokens=1000,
        ),
        AgentConfig(
            "analyst_cloud_b",
            "CLOUD",
            "ollama",
            "gemma2:2b",
            "Analista de Ética (Master)",
            max_tokens=1000,
        ),
    ]

    # Cruce híbrido: crítico local examina análisis nube y viceversa
    CRITIQUE_MAPPING = {
        "critic_local_a": (
            "analyst_local_a",
            "LOCAL",
            "ollama",
            "Crítico A (Worker)",
            "qwen2.5:3b",
        ),
        "critic_local_b": (
            "analyst_local_b",
            "LOCAL",
            "ollama",
            "Crítico B (Worker)",
            "phi3:mini",
        ),
        "critic_cloud_a": (
            "analyst_cloud_a",
            "CLOUD",
            "ollama",
            "Crítico C (Master)",
            "phi3:latest",
        ),
        "critic_cloud_b": (
            "analyst_cloud_b",
            "CLOUD",
            "ollama",
            "Crítico D (Master)",
            "mistral:latest",
        ),
    }

    SYNTHESIS_AGENTS = [
        AgentConfig(
            "synth_local",
            "LOCAL",
            "ollama",
            "deepseek-r1:7b",
            "Sintetizador Worker",
            max_tokens=1000,
        ),
        AgentConfig(
            "synth_cloud",
            "CLOUD",
            "ollama",
            "qwen2.5-coder:7b",
            "Sintetizador Master",
            max_tokens=1000,
        ),
    ]

    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.prompt_builder = PromptBuilder()
        self.tribunal = TribunalCouncil()

    async def execute_round(
        self,
        session_id: str,
        round_number: int,
        query: str,
        db_session: AsyncSession,
        max_rounds: int = 3,
        previous_context: Optional[str] = None,
        on_event: Optional[Callable[[str, Any], None]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta una ronda completa de debate (Fases 1-3, Tribunal en Fase 2)

        Retorna dict con resultados de la ronda
        """
        # Crear registro de ronda
        round_id = str(uuid.uuid4())
        round_record = Round(
            id=round_id,
            session_id=session_id,
            round_number=round_number,
            status="RUNNING",
            started_at=datetime.utcnow(),
        )
        db_session.add(round_record)
        await db_session.commit()

        logger.info(
            "round.started",
            session_id=session_id,
            round_number=round_number,
            round_id=round_id,
        )

        if on_event:
            on_event("round_started", {"round_number": round_number, "round_id": round_id})

        try:
            # ═══════════════════════════════════════════════════
            # FASE 1: ANÁLISIS (4 analistas en paralelo)
            # ═══════════════════════════════════════════════════

            if on_event:
                on_event(
                    "phase_started",
                    {
                        "phase": "ANALYSIS",
                        "agents": [a.slot for a in self.ANALYSIS_AGENTS],
                    },
                )

            analysis_results = await self._execute_analysis_phase(
                session_id=session_id,
                round_id=round_id,
                round_number=round_number,
                query=query,
                db_session=db_session,
                previous_context=previous_context,
                on_event=on_event,
            )

            if self.orchestrator.check_failure_threshold(analysis_results, 0.5):
                raise RuntimeError("Fase de análisis abortada: >50% de agentes fallaron")

            # ═══════════════════════════════════════════════════
            # FASE 2: CRÍTICA (cruce híbrido)
            # ═══════════════════════════════════════════════════

            if on_event:
                on_event(
                    "phase_started",
                    {"phase": "CRITIQUE", "mapping": self.CRITIQUE_MAPPING},
                )

            critique_results = await self._execute_critique_phase(
                session_id=session_id,
                round_id=round_id,
                round_number=round_number,
                analysis_results=analysis_results,
                db_session=db_session,
                on_event=on_event,
            )

            # ═══════════════════════════════════════════════════
            # FASE 3: SÍNTESIS
            # ═══════════════════════════════════════════════════

            if on_event:
                on_event("phase_started", {"phase": "SYNTHESIS"})

            synthesis_results = await self._execute_synthesis_phase(
                session_id=session_id,
                round_id=round_id,
                round_number=round_number,
                query=query,
                analysis_results=analysis_results,
                critique_results=critique_results,
                db_session=db_session,
                on_event=on_event,
            )

            # ═══════════════════════════════════════════════════
            # FASE 4: TRIBUNAL DE MAGISTRADOS (Fase 2+)
            # ═══════════════════════════════════════════════════

            local_synth = synthesis_results.get(
                "synth_local",
                AgentResult(call_id="", slot="synth_local", node="LOCAL", status="FAILED"),
            )
            cloud_synth = synthesis_results.get(
                "synth_cloud",
                AgentResult(call_id="", slot="synth_cloud", node="CLOUD", status="FAILED"),
            )

            tribunal_verdict = None
            # El tribunal corre si hay al menos una síntesis (local o cloud)
            if local_synth.response or cloud_synth.response:
                if on_event:
                    on_event("phase_started", {"phase": "TRIBUNAL"})

                tribunal_verdict = await self.tribunal.issue_verdict(
                    session_id=session_id,
                    round_id=round_id,
                    round_number=round_number,
                    query=query,
                    local_synthesis=local_synth.response or "",
                    cloud_synthesis=cloud_synth.response or "",
                    db_session=db_session,
                    on_event=on_event,
                )

                if on_event:
                    on_event(
                        "tribunal_verdict",
                        {
                            "consensus_reached": tribunal_verdict.consensus_reached,
                            "iterations": tribunal_verdict.iterations_required,
                            "evidence_score": tribunal_verdict.evidence_score,
                            "risk_score": tribunal_verdict.risk_score,
                        },
                    )

            # Completar ronda
            round_record.status = "COMPLETED"
            round_record.completed_at = datetime.utcnow()
            await db_session.commit()

            logger.info(
                "round.completed",
                session_id=session_id,
                round_number=round_number,
            )

            if on_event:
                on_event("round_completed", {"round_number": round_number})

            return {
                "round_id": round_id,
                "round_number": round_number,
                "status": "COMPLETED",
                "analysis": {slot: r.response for slot, r in analysis_results.items() if r.response},
                "critique": {slot: r.response for slot, r in critique_results.items() if r.response},
                "synthesis": {slot: r.response for slot, r in synthesis_results.items() if r.response},
                "tribunal_verdict": {
                    "verdict_text": tribunal_verdict.verdict_text if tribunal_verdict else None,
                    "consensus_reached": tribunal_verdict.consensus_reached if tribunal_verdict else False,
                    "iterations_required": tribunal_verdict.iterations_required if tribunal_verdict else 0,
                    "evidence_score": tribunal_verdict.evidence_score if tribunal_verdict else 0,
                    "risk_score": tribunal_verdict.risk_score if tribunal_verdict else 0,
                    "alignment_score": tribunal_verdict.alignment_score if tribunal_verdict else 0,
                }
                if tribunal_verdict
                else None,
            }

        except Exception as e:
            round_record.status = "FAILED"
            round_record.completed_at = datetime.utcnow()
            await db_session.commit()

            logger.error(
                "round.failed",
                session_id=session_id,
                round_number=round_number,
                error=str(e),
            )
            raise

    async def _execute_analysis_phase(
        self,
        session_id: str,
        round_id: str,
        round_number: int,
        query: str,
        db_session: AsyncSession,
        previous_context: Optional[str] = None,
        on_event: Optional[Callable] = None,
    ) -> Dict[str, AgentResult]:
        """Fase 1: Ejecuta 4 analistas en paralelo"""

        # Construir prompts
        prompts = {}
        for config in self.ANALYSIS_AGENTS:
            system_prompt = ""  # El prompt del rol va en user_prompt para compatibilidad
            user_prompt = self.prompt_builder.build_analyst_prompt(
                agent_slot=config.slot,
                query=query,
                role_label=config.role_label,
                max_tokens=config.max_tokens,
                context=previous_context,
            )
            prompts[config.slot] = (system_prompt, user_prompt)

        # Llamar en paralelo
        def on_token(slot: str, token: str, model_name: str, phase_name: str):
            if on_event:
                on_event(
                    "agent_token",
                    {
                        "phase": "ANALYSIS",
                        "agent": slot,
                        "token": token,
                        "model": model_name,
                    },
                )

        # Para que el callback reciba el modelo, necesitamos ajustar AgentOrchestrator.call_agent
        # o envolverlo aquí. Optaré por envolverlo en AgentOrchestrator para mayor limpieza.

        results = await self.orchestrator.call_agents_parallel(
            session_id=session_id,
            round_id=round_id,
            round_number=round_number,
            phase="ANALYSIS",
            agent_configs=self.ANALYSIS_AGENTS,
            prompts=prompts,
            db_session=db_session,
            on_agent_token=on_token,
        )

        if on_event:
            for slot, result in results.items():
                on_event(
                    "agent_completed",
                    {
                        "phase": "ANALYSIS",
                        "agent": slot,
                        "status": result.status,
                        "tokens": result.tokens_out,
                    },
                )

        return results

    async def _execute_critique_phase(
        self,
        session_id: str,
        round_id: str,
        round_number: int,
        analysis_results: Dict[str, AgentResult],
        db_session: AsyncSession,
        on_event: Optional[Callable] = None,
    ) -> Dict[str, AgentResult]:
        """Fase 2: Crítica con cruce híbrido"""

        # Construir configs de críticos según mapeo
        critique_configs = []
        for critic_slot, (
            target_slot,
            node,
            engine,
            role_label,
            model,
        ) in self.CRITIQUE_MAPPING.items():
            analysis_results.get(target_slot)

            config = AgentConfig(
                slot=critic_slot,
                node=node,
                engine=engine,
                model=model,
                role_label=role_label,
                max_tokens=1500,
            )
            critique_configs.append(config)

        # Construir texto de todos los análisis para el contexto global de los críticos
        all_analyses_text = "\n\n".join(
            [f"--- ANÁLISIS DE {res.slot} ---\n{res.response}" for res in analysis_results.values() if res.response]
        )

        # Construir prompts con el cruce
        prompts = {}
        critique_sources: Dict[str, str] = {}
        for config in critique_configs:
            target_slot = self.CRITIQUE_MAPPING[config.slot][0]
            target_analysis = analysis_results.get(target_slot)

            if not target_analysis or not target_analysis.response:
                logger.warning("critique_target_missing", critic=config.slot, target=target_slot)
                continue

            # Preparar contexto global excluyendo el target si se desea,
            # pero mejor pasarlo todo y que el modelo identifique.

            user_prompt = self.prompt_builder.build_critic_prompt(
                agent_slot=config.slot,
                target_analysis=target_analysis.response,
                other_analyses=all_analyses_text,
                role_label=config.role_label,
                max_tokens=config.max_tokens,
            )
            prompts[config.slot] = ("", user_prompt)

            if target_analysis.call_id:
                critique_sources[config.slot] = target_analysis.call_id

        # Ejecutar críticas en paralelo
        def on_token(slot: str, token: str, model_name: str, phase_name: str):
            if on_event:
                on_event(
                    "agent_token",
                    {
                        "phase": phase_name,
                        "agent": slot,
                        "token": token,
                        "model": model_name,
                    },
                )

        results = await self.orchestrator.call_agents_parallel(
            session_id=session_id,
            round_id=round_id,
            round_number=round_number,
            phase="CRITIQUE",
            agent_configs=critique_configs,
            prompts=prompts,
            db_session=db_session,
            on_agent_token=on_token,
        )

        for slot, result in results.items():
            source_call_id = critique_sources.get(slot)
            if result.call_id and source_call_id:
                await self.orchestrator.create_cross_references(
                    consumer_call_id=result.call_id,
                    source_call_ids=[source_call_id],
                    context_type="CRITIQUE_INPUT",
                    db_session=db_session,
                )

        if on_event:
            for slot, result in results.items():
                on_event(
                    "agent_completed",
                    {"phase": "CRITIQUE", "agent": slot, "status": result.status},
                )

        return results

    async def _execute_synthesis_phase(
        self,
        session_id: str,
        round_id: str,
        round_number: int,
        query: str,
        analysis_results: Dict[str, AgentResult],
        critique_results: Dict[str, AgentResult],
        db_session: AsyncSession,
        on_event: Optional[Callable] = None,
    ) -> Dict[str, AgentResult]:
        """Fase 3: Síntesis por nodo"""

        # Separar por nodo
        local_analyses = {}
        cloud_analyses = {}
        local_critiques = {}
        cloud_critiques = {}

        for slot, result in analysis_results.items():
            if result.response:
                if "local" in slot:
                    local_analyses[slot] = result.response
                else:
                    cloud_analyses[slot] = result.response

        for slot, result in critique_results.items():
            if result.response:
                if "local" in slot:
                    local_critiques[slot] = result.response
                else:
                    cloud_critiques[slot] = result.response

        # Construir prompts de síntesis
        prompts = {}

        # Síntesis Local (recibe críticas de nube sobre análisis locales)
        synth_local_prompt = self.prompt_builder.build_synthesis_prompt(
            node="LOCAL",
            query=query,
            analyses=local_analyses,
            critiques=cloud_critiques,
            max_tokens=2000,
            role_label=self.SYNTHESIS_AGENTS[0].role_label,
        )
        prompts["synth_local"] = ("", synth_local_prompt)

        # Síntesis Cloud (recibe críticas locales sobre análisis nube)
        if len(self.SYNTHESIS_AGENTS) > 1:
            synth_cloud_prompt = self.prompt_builder.build_synthesis_prompt(
                node="CLOUD",
                query=query,
                analyses=cloud_analyses,
                critiques=local_critiques,
                max_tokens=2000,
                role_label=self.SYNTHESIS_AGENTS[1].role_label,
            )
            prompts["synth_cloud"] = ("", synth_cloud_prompt)

        # Ejecutar síntesis
        def on_token(slot: str, token: str, model_name: str, phase_name: str):
            if on_event:
                on_event(
                    "agent_token",
                    {
                        "phase": phase_name,
                        "agent": slot,
                        "token": token,
                        "model": model_name,
                    },
                )

        results = await self.orchestrator.call_agents_parallel(
            session_id=session_id,
            round_id=round_id,
            round_number=round_number,
            phase="NODE_SYNTHESIS",
            agent_configs=self.SYNTHESIS_AGENTS,
            prompts=prompts,
            db_session=db_session,
            on_agent_token=on_token,
        )

        if on_event:
            for slot, result in results.items():
                on_event(
                    "agent_completed",
                    {"phase": "SYNTHESIS", "agent": slot, "status": result.status},
                )

        return results
