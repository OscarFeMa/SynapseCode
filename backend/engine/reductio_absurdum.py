"""
Synapse Council v2.3 - Reductio ad Absurdum Engine
Técnica lógica de reducción al absurdo para eliminar sesgos de complacencia en Ronda 2+.

Principio:
- Tomar cada conclusión/punto de acuerdo
- Llevarla a sus consecuencias extremas
- Identificar si genera contradicciones
- Usar para refinar argumentos y detectar suposiciones no cuestionadas

Objetivo: Evitar que el debate colapse prematuramente en consenso sin pensar críticamente.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import structlog

logger = structlog.get_logger()


@dataclass
class AbsurdumProof:
    """Resultado de aplicar reducción al absurdo a una proposición"""

    proposition: str  # Proposición original
    extreme_case: str  # Caso extremo derivado
    contradiction: Optional[str]  # Contradicción encontrada o None
    is_valid: bool  # ¿La proposición resiste al absurdo?
    confidence_score: float  # 0.0-1.0
    questioning_agent: str  # Agente que planteó el desafío
    challenged_agent: str  # Agente cuyo argumento fue desafiado
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ComplacencyScan:
    """Análisis de complacencia en el debate actual"""

    consensus_areas: List[str]  # Áreas donde hay acuerdo
    weak_assumptions: List[str]  # Supuestos no validados
    unquestioned_premises: List[str]  # Premisas no cuestionadas
    overall_complacency_risk: float = 0.0  # 0.0-1.0, nivel de riesgo de complacencia
    absurdum_proofs: List[AbsurdumProof] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class ReductioAbsurdumEngine:
    """
    Motor de Reducción al Absurdo.

    Detecta puntos donde el debate puede estar siendo complaciente y aplica técnica
    de llevar proposiciones a su límite lógico para identificar si son válidas.
    """

    # Frases de transición para derivar casos extremos
    EXTREME_DERIVATIONS = [
        "Si esto fuera cierto al 100%, entonces:",
        "Extrapolando esta lógica al máximo:",
        "Si asumimos esto sin límites:",
        "En el caso más extremo posible:",
        "Llevando esta idea al absurdo:",
        "Si esto se aplicara universalmente sin excepción:",
        "Suponiendo el escenario más radical:",
        "Extendiendo al infinito esta premisa:",
        "En la versión más extrema de tu argumento:",
        "Si esta tendencia continuara indefinidamente:",
    ]

    CONTRADICTION_MARKERS = [
        "esto contradice",
        "esto viola",
        "esto entra en conflicto con",
        "esto es incompatible con",
        "esto refuta",
        "esto anula",
        "esto es inconsistente con",
        "esto destruye",
        "esto socava",
        "esto niega",
    ]

    def __init__(self):
        self.proofs_history: List[AbsurdumProof] = []
        self.complacency_history: List[ComplacencyScan] = []

    def analyze_consensus_points(
        self,
        consensus_points: List[str],
        dissent_points: List[str],
        debate_history: str,
        iteration_number: int,
    ) -> ComplacencyScan:
        """
        Analiza los puntos de consenso para detectar potencial complacencia.

        Args:
            consensus_points: Puntos donde hay acuerdo
            dissent_points: Puntos donde hay desacuerdo
            debate_history: Historial del debate hasta ahora
            iteration_number: Número de iteración (1, 2, 3...)

        Returns:
            ComplacencyScan con análisis de riesgo
        """

        logger.info(
            "reductio_absurdum.analyzing_consensus",
            consensus_count=len(consensus_points),
            dissent_count=len(dissent_points),
            iteration=iteration_number,
        )

        scan = ComplacencyScan(
            consensus_areas=consensus_points.copy(),
            weak_assumptions=[],
            unquestioned_premises=[],
        )

        # Detectar suposiciones débiles (consenso sin suficiente debate)
        weak_assumptions = self._detect_weak_assumptions(consensus_points, dissent_points, iteration_number)
        scan.weak_assumptions = weak_assumptions

        # Detectar premisas no cuestionadas
        unquestioned = self._detect_unquestioned_premises(consensus_points, debate_history)
        scan.unquestioned_premises = unquestioned

        # Calcular riesgo de complacencia
        complacency_risk = self._calculate_complacency_risk(
            consensus_areas=consensus_points,
            weak_assumptions=weak_assumptions,
            unquestioned_premises=unquestioned,
            iteration_number=iteration_number,
        )
        scan.overall_complacency_risk = complacency_risk

        # Generar recomendaciones
        if complacency_risk > 0.6:
            scan.recommendations = [
                f"⚠️ RIESGO DE COMPLACENCIA ALTO ({complacency_risk:.0%})",
                "Se recomienda aplicar Reducción al Absurdo a estos puntos:",
                *[f"  • {point[:80]}..." for point in weak_assumptions[:3]],
                "Desafiar estas premisas sin cuestionamiento:",
                *[f"  • {point[:80]}..." for point in unquestioned[:3]],
            ]
        elif complacency_risk > 0.35:
            scan.recommendations = [
                f"⚠️ RIESGO MODERADO DE COMPLACENCIA ({complacency_risk:.0%})",
                "Considerar desafíos adicionales a:",
                *[f"  • {point[:80]}..." for point in weak_assumptions[:2]],
            ]
        else:
            scan.recommendations = [f"✅ DEBATE ROBUSTO - Bajo riesgo de complacencia ({complacency_risk:.0%})"]

        self.complacency_history.append(scan)
        logger.info(
            "reductio_absurdum.scan_complete",
            complacency_risk=complacency_risk,
            weak_assumptions=len(weak_assumptions),
            unquestioned=len(unquestioned),
        )

        return scan

    def _detect_weak_assumptions(
        self,
        consensus_points: List[str],
        dissent_points: List[str],
        iteration_number: int,
    ) -> List[str]:
        """Detecta puntos de consenso que podrían ser supuestos débiles"""

        weak = []

        # Si hay consenso en iteración temprana sin suficiente debate, es débil
        if iteration_number <= 2 and len(consensus_points) > len(dissent_points) * 2:
            weak.extend([p for p in consensus_points[:3]])

        # Puntos de consenso muy cortos (poco desarrollados) = débiles
        for point in consensus_points:
            if len(point) < 50:  # Menos de 50 caracteres = poco sustancia
                weak.append(point)

        # Puntos que contienen afirmaciones absolutas (sin matices) = débiles
        absolute_markers = [
            "siempre",
            "nunca",
            "imposible",
            "seguro",
            "definitivamente",
            "100%",
        ]
        for point in consensus_points:
            point_lower = point.lower()
            if any(marker in point_lower for marker in absolute_markers):
                weak.append(point)

        return list(dict.fromkeys(weak))  # Eliminar duplicados manteniendo orden

    def _detect_unquestioned_premises(self, consensus_points: List[str], debate_history: str) -> List[str]:
        """Detecta premisas que no han sido cuestionadas explícitamente"""

        unquestioned = []

        for point in consensus_points:
            # Si el punto no aparece cuestionado en el historial, es no cuestionado
            if not self._appears_questioned_in_history(point, debate_history):
                unquestioned.append(point)

        return unquestioned[:5]  # Limitar a top 5

    def _appears_questioned_in_history(self, point: str, history: str) -> bool:
        """Verifica si una proposición fue cuestionada en el debate"""

        # Palabras clave que indican cuestionamiento
        challenge_words = [
            "pero",
            "sin embargo",
            "objeta",
            "critica",
            "falla",
            "problema",
            "riesgo",
            "limitación",
            "contrario",
            "opuesto",
            "desacuerdo",
        ]

        point_keywords = point.split()[:5]  # Primeras 5 palabras
        history_lower = history.lower()

        # Verificar si el punto aparece junto con palabras de desafío
        for keyword in point_keywords:
            if keyword.lower() in history_lower:
                # Buscar palabras de desafío cercanas
                for challenge in challenge_words:
                    if challenge in history_lower:
                        return True

        return False

    def _calculate_complacency_risk(
        self,
        consensus_areas: List[str],
        weak_assumptions: List[str],
        unquestioned_premises: List[str],
        iteration_number: int,
    ) -> float:
        """
        Calcula el riesgo de complacencia (0.0-1.0).

        Factores:
        - Proporción de consenso vs total
        - Número de supuestos débiles
        - Premisas no cuestionadas
        - Número de iteración (más rondas = menos riesgo)
        """

        # Factor 1: Demasiado consenso temprano
        consensus_ratio = len(consensus_areas) / max(len(consensus_areas) + 1, 1)
        early_consensus_risk = consensus_ratio * (1 - iteration_number / 5)

        # Factor 2: Supuestos débiles
        weak_ratio = len(weak_assumptions) / max(len(consensus_areas), 1)
        weak_assumption_risk = min(weak_ratio, 1.0)

        # Factor 3: Premisas no cuestionadas
        unquestioned_ratio = len(unquestioned_premises) / max(len(consensus_areas), 1)
        unquestioned_risk = min(unquestioned_ratio * 0.7, 1.0)

        # Combinar factores (media ponderada)
        total_risk = early_consensus_risk * 0.4 + weak_assumption_risk * 0.35 + unquestioned_risk * 0.25

        return min(total_risk, 1.0)

    def generate_absurdum_challenge(self, proposition: str, agent_name: str) -> str:
        """
        Genera un desafío usando reducción al absurdo.

        Args:
            proposition: Proposición a desafiar
            agent_name: Nombre del agente que plantea el desafío

        Returns:
            Prompt de desafío para el modelo
        """

        import random

        derivation = random.choice(self.EXTREME_DERIVATIONS)

        prompt = f"""# DESAFÍO DE REDUCCIÓN AL ABSURDO

Proposición Original:
"{proposition}"

Tu tarea es aplicar la técnica de **Reducción al Absurdo**:

1. **Extrapolación**: {derivation}
   - Proyecta esta idea a su límite lógico
   - Identifica las consecuencias extremas

2. **Identificación de Contradicción**:
   - ¿Genera inconsistencias?
   - ¿Entra en conflicto con principios establecidos?
   - ¿Viola intuiciones fundamentales?

3. **Conclusión**:
   - ¿La proposición es válida incluso en el caso extremo?
   - ¿Necesita refinamiento o tiene fallas lógicas?
   - ¿Qué debería modificarse?

INSTRUCCIONES:
- Sé específico y riguroso en la lógica
- Cita la contradicción exacta encontrada
- Proporciona una alternativa más robusta
- Mantén un tono profesional pero crítico

Responde en máximo 300 palabras con estructura clara."""

        return prompt

    def generate_tribunal_self_challenge_prompt(self, magistrate_verdict: str, magistrate_role: str) -> str:
        """
        Genera un prompt para que el magistrado se desafíe a sí mismo.
        Usado en ronda 2 para eliminar el sesgo del magistrado (self-complacency).

        Args:
            magistrate_verdict: Veredicto emitido por el magistrado
            magistrate_role: Rol del magistrado (evidence, risk, alignment)

        Returns:
            Prompt de auto-desafío
        """

        role_self_doubts = {
            "evidence": [
                "¿Pasaste por alto evidencia contradictoria?",
                "¿Tu evaluación fue demasiado cerrada o rígida?",
                "¿Asumiste como válidas fuentes que merecían escepticismo?",
            ],
            "risk": [
                "¿Exageraste los riesgos para parecer prudente?",
                "¿Ignoraste oportunidades por exceso de precaución?",
                "¿Tu análisis de riesgos fue parcial?",
            ],
            "alignment": [
                "¿Priorizaste la alineación por sobre la verdad?",
                "¿Evitaste conclusiones incómodas?",
                "¿Tu síntesis fue un compromiso fácil en lugar de robusto?",
            ],
        }

        self_doubts = role_self_doubts.get(
            magistrate_role,
            [
                "¿Tu conclusión fue demasiado rápida?",
                "¿Ignoraste argumentos válidos?",
                "¿Tu veredicto podría mejorarse?",
            ],
        )

        selected_doubt = self_doubts[0]  # Top concern

        prompt = f"""# AUTO-CUESTIONAMIENTO DEL MAGISTRADO

Eres el Magistrado de {magistrate_role.upper()}.

Tu veredicto anterior fue:
"{magistrate_verdict}"

Se ha cuestionado tu sesgo inherente. Debes cuestionarte a ti mismo:

**Pregunta Principal:**
{selected_doubt}

**Ejercicio de Reducción al Absurdo:**
1. Toma tu conclusión principal
2. Asuméla como 100% correcta
3. Llévala a su conclusión más extrema
4. ¿Sigue siendo válida? ¿O se vuelve absurda?

**Respuesta Esperada:**
- Identifica al menos 1 debilidad en tu veredicto original
- Proporciona 1 premisa que asumiste sin validar completamente
- Sugiere 1 refinamiento basado en este análisis

Sé honesto y crítico. Un buen magistrado reconoce sus sesgos."""

        return prompt

    def extract_propositions_from_text(self, text: str) -> List[str]:
        """Extrae proposiciones principales de un texto de debate"""

        propositions = []

        # Dividir por puntos
        sentences = text.split(".")

        for sentence in sentences:
            sentence = sentence.strip()

            # Filtrar sentencias vacías o muy cortas
            if len(sentence) < 20:
                continue

            # Filtrar sentencias que son preguntas o instrucciones
            if sentence.endswith("?") or sentence.startswith("Por favor") or sentence.startswith("Nota"):
                continue

            propositions.append(sentence)

        return propositions[:5]  # Top 5 proposiciones más importantes

    def rank_propositions_by_robustness(self, propositions: List[str]) -> List[Tuple[str, float]]:
        """
        Ordena proposiciones por robustez (qué tan resistentes son al cuestionamiento).

        Retorna: [(proposición, robustness_score), ...]
        """

        ranked = []

        for prop in propositions:
            robustness = self._calculate_robustness_score(prop)
            ranked.append((prop, robustness))

        # Ordenar por robustness (menor = menos robusto = mejor para desafiar)
        return sorted(ranked, key=lambda x: x[1])

    def _calculate_robustness_score(self, proposition: str) -> float:
        """Calcula cuán robusto es un enunciado (0.0-1.0)"""

        score = 0.5  # Score base

        # Proposiciones con matices son más robustas
        nuance_words = [
            "puede",
            "podría",
            "probablemente",
            "a menudo",
            "generalmente",
            "en algunos casos",
        ]
        if any(word in proposition.lower() for word in nuance_words):
            score += 0.2

        # Proposiciones que citan evidencia son más robustas
        if "según" in proposition.lower() or "demostrado" in proposition.lower():
            score += 0.15

        # Proposiciones absolutas son menos robustas
        absolute_words = ["siempre", "nunca", "imposible", "definitivamente", "100%"]
        if any(word in proposition.lower() for word in absolute_words):
            score -= 0.3

        # Proposiciones largas y desarrolladas son más robustas
        if len(proposition) > 200:
            score += 0.1

        return max(0.0, min(score, 1.0))

    async def run_absurdum_challenge_phase(
        self,
        topic: str,
        consensus_points: List[str],
        debate_history: str,
        challenging_agent,  # DebateAgent
        target_agent,  # DebateAgent
        generate_func,  # Función para generar respuesta
    ) -> Optional[AbsurdumProof]:
        """
        Ejecuta una fase de desafío usando reducción al absurdo.

        Args:
            topic: Tema del debate
            consensus_points: Puntos de consenso a desafiar
            debate_history: Historial del debate
            challenging_agent: Agente que plantea el desafío
            target_agent: Agente cuyo argumento será desafiado
            generate_func: Función async para generar respuesta del modelo

        Returns:
            AbsurdumProof con resultado del desafío
        """

        if not consensus_points:
            logger.warning("reductio_absurdum.no_consensus_to_challenge")
            return None

        # Seleccionar proposición más vulnerable
        ranked = self.rank_propositions_by_robustness(consensus_points)

        if ranked:
            target_proposition, robustness = ranked[0]
        else:
            target_proposition = consensus_points[0]
            robustness = 0.5

        logger.info(
            "reductio_absurdum.targeting_proposition",
            proposition_preview=target_proposition[:80],
            robustness=robustness,
            challenger=challenging_agent.name,
            target=target_agent.name,
        )

        # Generar desafío
        challenge_prompt = self.generate_absurdum_challenge(target_proposition, challenging_agent.name)

        try:
            # Obtener respuesta del modelo
            response = await generate_func(target_agent, challenge_prompt)

            # Detectar si reconoció contradicción
            contradiction_found = any(marker in response.lower() for marker in self.CONTRADICTION_MARKERS)

            proof = AbsurdumProof(
                proposition=target_proposition,
                extreme_case=response if response else "No response",
                contradiction=response if contradiction_found else None,
                is_valid=not contradiction_found,
                confidence_score=0.8 if contradiction_found else 0.6,
                questioning_agent=challenging_agent.name,
                challenged_agent=target_agent.name,
            )

            self.proofs_history.append(proof)

            logger.info(
                "reductio_absurdum.proof_generated",
                proposition_preview=target_proposition[:80],
                contradiction_found=contradiction_found,
            )

            return proof

        except Exception as e:
            logger.error(
                "reductio_absurdum.challenge_failed",
                error=str(e),
                challenger=challenging_agent.name,
            )
            return None


# Singleton instance
_reductio_engine = None


def get_reductio_absurdum_engine() -> ReductioAbsurdumEngine:
    """Obtiene la instancia singleton del motor de reducción al absurdo"""
    global _reductio_engine
    if _reductio_engine is None:
        _reductio_engine = ReductioAbsurdumEngine()
    return _reductio_engine
