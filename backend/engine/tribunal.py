"""
Synapse Council v2.0 - Tribunal de Magistrados
Implementa el Protocolo de Consenso Forzado (PCO) con 3 magistrados:
- Magistrado de Evidencias (auditor técnico)
- Magistrado de Riesgos (abogado del diablo)
- Magistrado de Alineación (product owner)

Ejecución configurable por rol, con preferencia local y fallback opcional.
"""

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.local_db import AsyncSessionLocal
from backend.engine.agent_orchestrator import (
    AgentOrchestrator,
    AgentResult,
)
from backend.engine.prompts import PromptBuilder
from backend.engine.reductio_absurdum import get_reductio_absurdum_engine
from backend.engine.reputation_service import get_reputation_service
from backend.engine.tribunal_config import TribunalRoleConfig, build_tribunal_config

settings = get_settings()
logger = structlog.get_logger()


@dataclass
class MagistrateOpinion:
    """Opinión de un magistrado"""

    role: str
    call_id: str
    blocking: bool
    response: str
    score: int  # 0-100
    iteration: int


@dataclass
class TribunalVerdict:
    """Veredicto final del Tribunal"""

    verdict_text: str
    consensus_reached: bool
    iterations_required: int
    magistrate_opinions: Dict[str, MagistrateOpinion]
    evidence_score: int
    risk_score: int
    alignment_score: int
    dissent_areas: Optional[str] = None


class TribunalCouncil:
    """
    Tribunal de 3 Magistrados con Protocolo de Consenso Forzado (PCO):

    1. Alineación propone borrador
    2. Evidencias y Riesgos emiten objeciones de bloqueo
    3. Si hay objeción crítica → feedback a Alineación → corrección
    4. Máximo 3 iteraciones
    5. Si no hay acuerdo → resolución por méritos (dominio con mayor peso)

    Preferencia local con fallback configurable por rol.
    """

    MAX_ITERATIONS = settings.TRIBUNAL_MAX_ITERATIONS

    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.prompt_builder = PromptBuilder()
        self.reductio_engine = get_reductio_absurdum_engine()  # Motor de Reducción al Absurdo
        self.role_configs = build_tribunal_config(settings)
        self.MAGISTRATES = {role: role_config.primary for role, role_config in self.role_configs.items()}

    def get_role_config(self, role: str) -> TribunalRoleConfig:
        return self.role_configs[role]

    async def _call_magistrate_with_fallback(
        self,
        *,
        role: str,
        session_id: str,
        round_id: str,
        round_number: int,
        phase: str,
        prompt: str,
        db_session: AsyncSession,
        on_event: Optional[Callable[[str, Any], None]] = None,
    ) -> AgentResult:
        """Calls a magistrate using primary config, then configured fallbacks."""
        last_result: Optional[AgentResult] = None
        role_config = self.get_role_config(role)

        for attempt, config in enumerate(role_config.chain, start=1):
            if on_event and attempt > 1:
                on_event(
                    "tribunal_fallback",
                    {
                        "role": role,
                        "attempt": attempt,
                        "node": config.node,
                        "engine": config.engine,
                        "model": config.model,
                    },
                )

            result = await self.orchestrator.call_agent(
                session_id=session_id,
                round_id=round_id,
                round_number=round_number,
                phase=phase,
                config=config,
                system_prompt="",
                user_prompt=prompt,
                db_session=db_session,
                on_token=lambda t: on_event("tribunal_token", {"role": role, "token": t}) if on_event else None,
            )
            last_result = result

            if result.status == "COMPLETED" and result.response:
                if attempt > 1:
                    logger.info(
                        "tribunal.fallback_succeeded",
                        role=role,
                        attempt=attempt,
                        model=config.model,
                    )
                return result

            logger.warning(
                "tribunal.magistrate_attempt_failed",
                role=role,
                attempt=attempt,
                node=config.node,
                engine=config.engine,
                model=config.model,
                status=result.status,
                error=result.error_message,
            )

        return last_result or AgentResult(
            call_id="",
            slot=role,
            node="UNKNOWN",
            status="FAILED",
            response="FALLO_DE_SISTEMA: 0/100",
        )

    async def issue_verdict(
        self,
        session_id: str,
        round_id: str,
        round_number: int,
        query: str,
        local_synthesis: str,
        cloud_synthesis: str,
        db_session: AsyncSession,
        on_event: Optional[Callable[[str, Any], None]] = None,
    ) -> TribunalVerdict:
        """
        Emite veredicto mediante Protocolo de Consenso Forzado
        con ponderación por reputación EMA de cada modelo.
        """
        logger.info(
            "tribunal.verdict_start",
            session_id=session_id,
            round_number=round_number,
        )

        if on_event:
            on_event("tribunal_started", {"round_number": round_number})

        opinions_history: Dict[str, list] = {
            "evidence": [],
            "risk": [],
            "alignment": [],
        }

        # Cargar scores de reputación para los modelos del tribunal
        rep_service = get_reputation_service()
        rep_scores = {}
        for role, config in self.MAGISTRATES.items():
            score = await rep_service.get_score(config.model, role)
            rep_scores[role] = score
            logger.info(
                "tribunal.reputation_loaded",
                role=role,
                model=config.model,
                score=round(score.reputation_score, 3),
            )

        for iteration in range(1, self.MAX_ITERATIONS + 1):
            logger.info(
                "tribunal.iteration",
                session_id=session_id,
                iteration=iteration,
            )

            if on_event:
                on_event(
                    "tribunal_iteration",
                    {"iteration": iteration, "max_iterations": self.MAX_ITERATIONS},
                )

            # ═════════════════════════════════════════════════════
            # PASO 1: Alineación propone borrador
            # ═════════════════════════════════════════════════════

            evidence_input = opinions_history["evidence"][-1].response if opinions_history["evidence"] else None
            risk_input = opinions_history["risk"][-1].response if opinions_history["risk"] else None

            alignment_prompt = self.prompt_builder.build_magistrate_prompt(
                role="alignment",
                query=query,
                local_synthesis=local_synthesis,
                cloud_synthesis=cloud_synthesis,
                evidence_input=evidence_input,
                risk_input=risk_input,
                iteration=iteration,
                max_tokens=self.MAGISTRATES["alignment"].max_tokens,
            )

            alignment_result = await self._call_magistrate_with_fallback(
                role="alignment",
                session_id=session_id,
                round_id=round_id,
                round_number=round_number,
                phase="TRIBUNAL",
                prompt=alignment_prompt,
                db_session=db_session,
                on_event=on_event,
            )

            alignment_opinion = MagistrateOpinion(
                role="alignment",
                call_id=alignment_result.call_id,
                blocking=False,  # Alineación no bloquea
                response=alignment_result.response or "",
                score=self._extract_score(alignment_result.response or ""),
                iteration=iteration,
            )
            opinions_history["alignment"].append(alignment_opinion)

            if on_event:
                on_event(
                    "magistrate_complete",
                    {
                        "role": "alignment",
                        "iteration": iteration,
                        "status": alignment_result.status,
                    },
                )

            # ═════════════════════════════════════════════════════
            # PASO 2: Evidencias y Riesgos evalúan EN PARALELO
            # ═════════════════════════════════════════════════════

            # Preparar prompts
            evidence_prompt = self.prompt_builder.build_magistrate_prompt(
                role="evidence",
                query=query,
                local_synthesis=local_synthesis,
                cloud_synthesis=cloud_synthesis,
                max_tokens=self.MAGISTRATES["evidence"].max_tokens,
            )

            risk_prompt = self.prompt_builder.build_magistrate_prompt(
                role="risk",
                query=query,
                local_synthesis=local_synthesis,
                cloud_synthesis=cloud_synthesis,
                max_tokens=self.MAGISTRATES["risk"].max_tokens,
            )

            # Función helper para llamar a agente con su propia sesión (evita errores de concurrencia en SQLAlchemy)
            async def call_with_own_session(prompt, role):
                async with AsyncSessionLocal() as session:
                    return await self._call_magistrate_with_fallback(
                        role=role,
                        session_id=session_id,
                        round_id=round_id,
                        round_number=round_number,
                        phase="TRIBUNAL",
                        prompt=prompt,
                        db_session=session,
                        on_event=on_event,
                    )

            # Ejecutar ambos magistrados en paralelo con sesiones INDEPENDIENTES
            evidence_result, risk_result = await asyncio.gather(
                call_with_own_session(evidence_prompt, "evidence"),
                call_with_own_session(risk_prompt, "risk"),
                return_exceptions=True,
            )

            # Helper para procesar resultado
            def parse_magistrate_result(result, role_name):
                if isinstance(result, Exception):
                    logger.error("tribunal.magistrate_failed", role=role_name, error=str(result))
                    return AgentResult(
                        call_id="",
                        slot=role_name,
                        node="UNKNOWN",
                        status="FAILED",
                        response="FALLO_DE_SISTEMA: 0/100",
                    )
                if result.status != "COMPLETED" or not result.response:
                    logger.error(
                        "tribunal.magistrate_failed",
                        role=role_name,
                        status=result.status,
                        error=result.error_message,
                    )
                    return AgentResult(
                        call_id=result.call_id,
                        slot=result.slot,
                        node=result.node,
                        status=result.status,
                        response="FALLO_DE_SISTEMA: 0/100",
                        error_message=result.error_message,
                    )
                return result

            # Procesar resultado de Evidencias
            evidence_result_parsed = parse_magistrate_result(evidence_result, "evidence")
            evidence_blocking = self._has_blocking_objection(evidence_result_parsed.response or "")
            evidence_opinion = MagistrateOpinion(
                role="evidence",
                call_id=evidence_result_parsed.call_id,
                blocking=evidence_blocking,
                response=evidence_result_parsed.response or "",
                score=self._extract_score(evidence_result_parsed.response or ""),
                iteration=iteration,
            )
            opinions_history["evidence"].append(evidence_opinion)

            if on_event:
                on_event(
                    "tribunal_objection",
                    {
                        "role": "evidence",
                        "blocking": evidence_blocking,
                        "score": evidence_opinion.score,
                    },
                )

            # Procesar resultado de Riesgos
            risk_result_parsed = parse_magistrate_result(risk_result, "risk")
            risk_blocking = self._has_blocking_objection(risk_result_parsed.response or "")
            risk_opinion = MagistrateOpinion(
                role="risk",
                call_id=risk_result_parsed.call_id,
                blocking=risk_blocking,
                response=risk_result_parsed.response or "",
                score=self._extract_score(risk_result_parsed.response or ""),
                iteration=iteration,
            )
            opinions_history["risk"].append(risk_opinion)

            if on_event:
                on_event(
                    "tribunal_objection",
                    {
                        "role": "risk",
                        "blocking": risk_blocking,
                        "score": risk_opinion.score,
                    },
                )

            # ═════════════════════════════════════════════════════
            # FASE ADICIONAL: AUTO-CUESTIONAMIENTO (Ronda 2)
            # Magistrados se desafían a sí mismos usando Reducción al Absurdo
            # ═════════════════════════════════════════════════════
            if iteration == 2:
                logger.info(
                    "tribunal.self_challenge_phase",
                    session_id=session_id,
                    iteration=iteration,
                )

                # Cada magistrado se auto-cuestiona su veredicto
                await self._run_magistrate_self_challenge(
                    session_id=session_id,
                    opinions_history=opinions_history,
                    iteration=iteration,
                    on_event=on_event,
                )

            # ═════════════════════════════════════════════════════
            # PASO 3: ¿Hay consenso?
            # ═════════════════════════════════════════════════════

            if not evidence_blocking and not risk_blocking:
                # ✅ CONSENSO ALCANZADO
                logger.info(
                    "tribunal.consensus_reached",
                    session_id=session_id,
                    iterations=iteration,
                )

                if on_event:
                    on_event("tribunal_consensus", {"iterations": iteration})

                # Calcular scores ponderados por reputación
                rep_evidence = rep_scores["evidence"].reputation_score
                rep_risk = rep_scores["risk"].reputation_score
                rep_alignment = rep_scores["alignment"].reputation_score

                weighted_evidence = int(evidence_opinion.score * rep_evidence + 50 * (1 - rep_evidence))
                weighted_risk = int(risk_opinion.score * rep_risk + 50 * (1 - rep_risk))
                weighted_alignment = int(alignment_opinion.score * rep_alignment + 50 * (1 - rep_alignment))

                return TribunalVerdict(
                    verdict_text=alignment_opinion.response,
                    consensus_reached=True,
                    iterations_required=iteration,
                    magistrate_opinions={
                        "evidence": evidence_opinion,
                        "risk": risk_opinion,
                        "alignment": alignment_opinion,
                    },
                    evidence_score=weighted_evidence,
                    risk_score=weighted_risk,
                    alignment_score=weighted_alignment,
                    dissent_areas=None,
                )

            # Hay objeciones, continuar a siguiente iteración
            logger.info(
                "tribunal.objections_found",
                session_id=session_id,
                iteration=iteration,
                evidence_blocks=evidence_blocking,
                risk_blocks=risk_blocking,
            )

        # ═════════════════════════════════════════════════════
        # PASO 4: Sin consenso tras 3 iteraciones → Resolución por méritos
        # ═════════════════════════════════════════════════════

        logger.info(
            "tribunal.no_consensus",
            session_id=session_id,
            max_iterations=self.MAX_ITERATIONS,
        )

        if on_event:
            on_event("tribunal_no_consensus", {"max_iterations": self.MAX_ITERATIONS})

        # Determinar veredicto final por méritos
        final_alignment = opinions_history["alignment"][-1]
        final_evidence = opinions_history["evidence"][-1]
        final_risk = opinions_history["risk"][-1]

        # Scores ponderados por reputación
        rep_evidence = rep_scores["evidence"].reputation_score
        rep_risk = rep_scores["risk"].reputation_score
        rep_alignment = rep_scores["alignment"].reputation_score

        weighted_evidence = int(final_evidence.score * rep_evidence + 50 * (1 - rep_evidence))
        weighted_risk = int(final_risk.score * rep_risk + 50 * (1 - rep_risk))
        weighted_alignment = int(final_alignment.score * rep_alignment + 50 * (1 - rep_alignment))

        # Construir veredicto compuesto
        verdict_text = f"""{final_alignment.response}

---

## NOTA DEL TRIBUNAL
Este veredicto se emitió sin consenso completo tras {self.MAX_ITERATIONS} iteraciones del Protocolo de Consenso Forzado.

**Disentimientos pendientes:**

**Magistrado de Evidencias** (Score Técnico: {weighted_evidence}/100, Reputación EMA: {rep_evidence:.2f}):
{final_evidence.response[:500]}...

**Magistrado de Riesgos** (Score de Riesgo: {weighted_risk}/100, Reputación EMA: {rep_risk:.2f}):
{final_risk.response[:500]}...

**Resolución aplicada:** Veredicto del Magistrado de Alineación con notas de disentimiento.
"""

        dissent_areas = self._extract_dissent_areas(final_evidence.response, final_risk.response)

        return TribunalVerdict(
            verdict_text=verdict_text,
            consensus_reached=False,
            iterations_required=self.MAX_ITERATIONS,
            magistrate_opinions={
                "evidence": final_evidence,
                "risk": final_risk,
                "alignment": final_alignment,
            },
            evidence_score=weighted_evidence,
            risk_score=weighted_risk,
            alignment_score=weighted_alignment,
            dissent_areas=dissent_areas,
        )

        if on_event:
            on_event("tribunal_started", {"round_number": round_number})

        opinions_history: Dict[str, list] = {
            "evidence": [],
            "risk": [],
            "alignment": [],
        }

        for iteration in range(1, self.MAX_ITERATIONS + 1):
            logger.info(
                "tribunal.iteration",
                session_id=session_id,
                iteration=iteration,
            )

            if on_event:
                on_event(
                    "tribunal_iteration",
                    {"iteration": iteration, "max_iterations": self.MAX_ITERATIONS},
                )

            # ═════════════════════════════════════════════════════
            # PASO 1: Alineación propone borrador
            # ═════════════════════════════════════════════════════

            evidence_input = opinions_history["evidence"][-1].response if opinions_history["evidence"] else None
            risk_input = opinions_history["risk"][-1].response if opinions_history["risk"] else None

            alignment_prompt = self.prompt_builder.build_magistrate_prompt(
                role="alignment",
                query=query,
                local_synthesis=local_synthesis,
                cloud_synthesis=cloud_synthesis,
                evidence_input=evidence_input,
                risk_input=risk_input,
                iteration=iteration,
                max_tokens=self.MAGISTRATES["alignment"].max_tokens,
            )

            alignment_result = await self._call_magistrate_with_fallback(
                role="alignment",
                session_id=session_id,
                round_id=round_id,
                round_number=round_number,
                phase="TRIBUNAL",
                prompt=alignment_prompt,
                db_session=db_session,
                on_event=on_event,
            )

            alignment_opinion = MagistrateOpinion(
                role="alignment",
                call_id=alignment_result.call_id,
                blocking=False,  # Alineación no bloquea
                response=alignment_result.response or "",
                score=self._extract_score(alignment_result.response or ""),
                iteration=iteration,
            )
            opinions_history["alignment"].append(alignment_opinion)

            if on_event:
                on_event(
                    "magistrate_complete",
                    {
                        "role": "alignment",
                        "iteration": iteration,
                        "status": alignment_result.status,
                    },
                )

            # ═════════════════════════════════════════════════════
            # PASO 2: Evidencias y Riesgos evalúan EN PARALELO
            # ═════════════════════════════════════════════════════

            # Preparar prompts
            evidence_prompt = self.prompt_builder.build_magistrate_prompt(
                role="evidence",
                query=query,
                local_synthesis=local_synthesis,
                cloud_synthesis=cloud_synthesis,
                max_tokens=self.MAGISTRATES["evidence"].max_tokens,
            )

            risk_prompt = self.prompt_builder.build_magistrate_prompt(
                role="risk",
                query=query,
                local_synthesis=local_synthesis,
                cloud_synthesis=cloud_synthesis,
                max_tokens=self.MAGISTRATES["risk"].max_tokens,
            )

            # Función helper para llamar a agente con su propia sesión (evita errores de concurrencia en SQLAlchemy)
            async def call_with_own_session(prompt, role):
                async with AsyncSessionLocal() as session:
                    return await self._call_magistrate_with_fallback(
                        role=role,
                        session_id=session_id,
                        round_id=round_id,
                        round_number=round_number,
                        phase="TRIBUNAL",
                        prompt=prompt,
                        db_session=session,
                        on_event=on_event,
                    )

            # Ejecutar ambos magistrados en paralelo con sesiones INDEPENDIENTES
            evidence_result, risk_result = await asyncio.gather(
                call_with_own_session(evidence_prompt, "evidence"),
                call_with_own_session(risk_prompt, "risk"),
                return_exceptions=True,
            )

            # Helper para procesar resultado
            def parse_magistrate_result(result, role_name):
                if isinstance(result, Exception):
                    logger.error("tribunal.magistrate_failed", role=role_name, error=str(result))
                    return AgentResult(
                        call_id="",
                        slot=role_name,
                        node="UNKNOWN",
                        status="FAILED",
                        response="FALLO_DE_SISTEMA: 0/100",
                    )
                if result.status != "COMPLETED" or not result.response:
                    logger.error(
                        "tribunal.magistrate_failed",
                        role=role_name,
                        status=result.status,
                        error=result.error_message,
                    )
                    return AgentResult(
                        call_id=result.call_id,
                        slot=result.slot,
                        node=result.node,
                        status=result.status,
                        response="FALLO_DE_SISTEMA: 0/100",
                        error_message=result.error_message,
                    )
                return result

            # Procesar resultado de Evidencias
            evidence_result_parsed = parse_magistrate_result(evidence_result, "evidence")
            evidence_blocking = self._has_blocking_objection(evidence_result_parsed.response or "")
            evidence_opinion = MagistrateOpinion(
                role="evidence",
                call_id=evidence_result_parsed.call_id,
                blocking=evidence_blocking,
                response=evidence_result_parsed.response or "",
                score=self._extract_score(evidence_result_parsed.response or ""),
                iteration=iteration,
            )
            opinions_history["evidence"].append(evidence_opinion)

            if on_event:
                on_event(
                    "tribunal_objection",
                    {
                        "role": "evidence",
                        "blocking": evidence_blocking,
                        "score": evidence_opinion.score,
                    },
                )

            # Procesar resultado de Riesgos
            risk_result_parsed = parse_magistrate_result(risk_result, "risk")
            risk_blocking = self._has_blocking_objection(risk_result_parsed.response or "")
            risk_opinion = MagistrateOpinion(
                role="risk",
                call_id=risk_result_parsed.call_id,
                blocking=risk_blocking,
                response=risk_result_parsed.response or "",
                score=self._extract_score(risk_result_parsed.response or ""),
                iteration=iteration,
            )
            opinions_history["risk"].append(risk_opinion)

            if on_event:
                on_event(
                    "tribunal_objection",
                    {
                        "role": "risk",
                        "blocking": risk_blocking,
                        "score": risk_opinion.score,
                    },
                )

            # ═════════════════════════════════════════════════════
            # FASE ADICIONAL: AUTO-CUESTIONAMIENTO (Ronda 2)
            # Magistrados se desafían a sí mismos usando Reducción al Absurdo
            # ═════════════════════════════════════════════════════
            if iteration == 2:
                logger.info(
                    "tribunal.self_challenge_phase",
                    session_id=session_id,
                    iteration=iteration,
                )

                # Cada magistrado se auto-cuestiona su veredicto
                await self._run_magistrate_self_challenge(
                    session_id=session_id,
                    opinions_history=opinions_history,
                    iteration=iteration,
                    on_event=on_event,
                )

            # ═════════════════════════════════════════════════════
            # PASO 3: ¿Hay consenso?
            # ═════════════════════════════════════════════════════

            if not evidence_blocking and not risk_blocking:
                # ✅ CONSENSO ALCANZADO
                logger.info(
                    "tribunal.consensus_reached",
                    session_id=session_id,
                    iterations=iteration,
                )

                if on_event:
                    on_event("tribunal_consensus", {"iterations": iteration})

                return TribunalVerdict(
                    verdict_text=alignment_opinion.response,
                    consensus_reached=True,
                    iterations_required=iteration,
                    magistrate_opinions={
                        "evidence": evidence_opinion,
                        "risk": risk_opinion,
                        "alignment": alignment_opinion,
                    },
                    evidence_score=evidence_opinion.score,
                    risk_score=risk_opinion.score,
                    alignment_score=alignment_opinion.score,
                    dissent_areas=None,
                )

            # Hay objeciones, continuar a siguiente iteración
            logger.info(
                "tribunal.objections_found",
                session_id=session_id,
                iteration=iteration,
                evidence_blocks=evidence_blocking,
                risk_blocks=risk_blocking,
            )

        # ═════════════════════════════════════════════════════
        # PASO 4: Sin consenso tras 3 iteraciones → Resolución por méritos
        # ═════════════════════════════════════════════════════

        logger.info(
            "tribunal.no_consensus",
            session_id=session_id,
            max_iterations=self.MAX_ITERATIONS,
        )

        if on_event:
            on_event("tribunal_no_consensus", {"max_iterations": self.MAX_ITERATIONS})

        # Determinar veredicto final por méritos
        # Priorizar la perspectiva del magistrado con mayor score en su dominio
        final_alignment = opinions_history["alignment"][-1]
        final_evidence = opinions_history["evidence"][-1]
        final_risk = opinions_history["risk"][-1]

        # Construir veredicto compuesto
        verdict_text = f"""{final_alignment.response}

---

## NOTA DEL TRIBUNAL
Este veredicto se emitió sin consenso completo tras {self.MAX_ITERATIONS} iteraciones del Protocolo de Consenso Forzado.

**Disentimientos pendientes:**

**Magistrado de Evidencias** (Score Técnico: {final_evidence.score}/100):
{final_evidence.response[:500]}...

**Magistrado de Riesgos** (Score de Riesgo: {final_risk.score}/100):
{final_risk.response[:500]}...

**Resolución aplicada:** Veredicto del Magistrado de Alineación con notas de disentimiento.
"""

        dissent_areas = self._extract_dissent_areas(final_evidence.response, final_risk.response)

        return TribunalVerdict(
            verdict_text=verdict_text,
            consensus_reached=False,
            iterations_required=self.MAX_ITERATIONS,
            magistrate_opinions={
                "evidence": final_evidence,
                "risk": final_risk,
                "alignment": final_alignment,
            },
            evidence_score=final_evidence.score,
            risk_score=final_risk.score,
            alignment_score=final_alignment.score,
            dissent_areas=dissent_areas,
        )

    async def _run_magistrate_self_challenge(
        self,
        session_id: str,
        opinions_history: Dict[str, list],
        iteration: int,
        on_event: Optional[Callable[[str, Any], None]] = None,
    ):
        """
        FASE DE AUTO-CUESTIONAMIENTO (Ronda 2 del Tribunal)

        Cada magistrado se desafía a sí mismo usando Reducción al Absurdo
        para eliminar sesgos y complacencia inherentes a su rol.

        Objetivos:
        - Desafiar conclusiones demasiado rápidas
        - Identificar supuestos no validados
        - Refinar veredictos llevándolos al límite
        """

        try:
            logger.info(
                "tribunal.self_challenge_start",
                session_id=session_id,
                magistrates_count=3,
            )

            for role in ["evidence", "risk", "alignment"]:
                if not opinions_history.get(role):
                    continue

                current_opinion = opinions_history[role][-1]

                # Generar prompt de auto-cuestionamiento
                self_challenge_prompt = self.reductio_engine.generate_tribunal_self_challenge_prompt(
                    magistrate_verdict=current_opinion.response,
                    magistrate_role=role,
                )

                logger.info(
                    "tribunal.magistrate_self_challenge",
                    session_id=session_id,
                    role=role,
                    iteration=iteration,
                )

                try:
                    async with AsyncSessionLocal() as session:
                        challenge_result = await self._call_magistrate_with_fallback(
                            role=role,
                            session_id=session_id,
                            round_id=session_id,
                            round_number=iteration,
                            phase="TRIBUNAL_SELF_CHALLENGE",
                            prompt=self_challenge_prompt,
                            db_session=session,
                            on_event=on_event,
                        )

                    if on_event:
                        on_event(
                            "tribunal_self_challenge_complete",
                            {
                                "role": role,
                                "status": challenge_result.status,
                                "found_weakness": "debilidad" in challenge_result.response.lower()
                                or "falla" in challenge_result.response.lower(),
                            },
                        )

                    logger.info(
                        "tribunal.self_challenge_complete",
                        session_id=session_id,
                        role=role,
                        response_preview=challenge_result.response[:100],
                    )

                except Exception as e:
                    logger.warning(
                        "tribunal.self_challenge_failed",
                        session_id=session_id,
                        role=role,
                        error=str(e),
                    )

        except Exception as e:
            logger.error(
                "tribunal.self_challenge_phase_failed",
                session_id=session_id,
                error=str(e),
            )

    def _has_blocking_objection(self, response: str) -> bool:
        """
        Detecta si hay objeción de bloqueo en la respuesta
        Busca patrones como "Objeción de Bloqueo: SÍ" o similar
        """
        if not response:
            return False

        # Patrones de objeción con soporte para variaciones de encoding y acentos
        blocking_patterns = [
            r"##\s*Objeción de Bloqueo:\s*SÍ",
            r"##\s*Objeción de Bloqueo:\s*SI",
            r"##\s*Objecion de Bloqueo:\s*Sí",
            r"##\s*Objecion de Bloqueo:\s*Si",
            r"##\s*Objeción de Bloqueo:\s*Yes",
            r"Objeción de Bloqueo:\s*S[ÍIÍií]",
            r"Objecion de Bloqueo:\s*S[Iií]",
            r"Bloqueo:\s*S[ÍIÍií]",
            r"Blocking Objection:\s*Yes",
        ]

        response_upper = response.upper()

        for pattern in blocking_patterns:
            if re.search(pattern, response_upper):
                return True

        # Heurística: si score técnico < 50, considerar como bloqueo parcial
        score = self._extract_score(response)
        if score < 30:
            return True

        return False

    def _extract_score(self, response: str) -> int:
        """Extrae puntuación numérica de la respuesta (0-100)"""
        if not response:
            return 50

        patterns = [
            r"Puntuación\s+Técnica[^:]*:\s*(\d+)",
            r"Puntuación\s+de\s+Riesgo[^:]*:\s*(\d+)",
            r"(?:Score|Puntuación)[^:]*:\s*(\d+)\s*/\s*100",
            r"(?:Score|Puntuación)[^:]*:\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    score = int(match.group(1))
                    return max(0, min(100, score))  # Clamp 0-100
                except (ValueError, IndexError):
                    continue

        return 50  # Default neutral

    def _extract_dissent_areas(self, evidence_response: str, risk_response: str) -> str:
        """Extrae áreas de disentimiento de las respuestas"""
        dissent_parts = []

        # De Evidencias
        if "Argumentos Rechazados" in evidence_response:
            try:
                section = evidence_response.split("## Argumentos Rechazados")[1]
                section = section.split("##")[0]
                dissent_parts.append(f"Evidencias rechaza: {section[:300]}")
            except IndexError:
                pass

        # De Riesgos
        if "Riesgos Críticos" in risk_response:
            try:
                section = risk_response.split("### Críticos")[1]
                section = section.split("###")[0]
                dissent_parts.append(f"Riesgos identificados: {section[:300]}")
            except IndexError:
                pass

        return "\n".join(dissent_parts) if dissent_parts else "Disenso no detallado explícitamente"
