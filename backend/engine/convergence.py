"""
Synapse Council v2.0 - Convergence Evaluator
Evalúa si se ha alcanzado convergencia entre rondas para detener el debate.

Heurísticas:
1. Similitud temática entre síntesis local y cloud
2. Acuerdo en puntos clave
3. Reducción de áreas de disenso
4. Estabilidad de conclusiones entre rondas
"""

import re
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class ConvergenceResult:
    """Resultado de evaluación de convergencia"""

    consensus_reached: bool
    consensus_level: str  # CONSENSUS_REACHED | PARTIAL_CONSENSUS | DIVERGENT
    similarity_score: float  # 0.0 - 1.0
    should_stop: bool
    focus_for_next_round: str | None
    detail: dict[str, Any]


class ConvergenceEvaluator:
    """
    Evaluador de convergencia entre rondas de debate.
    Determina si se debe continuar o detener el debate.
    """

    # Umbrales de convergencia
    SIMILARITY_THRESHOLD = 0.75  # 75% de similitud = consenso
    PARTIAL_THRESHOLD = 0.50  # 50% = consenso parcial
    MAX_ROUNDS_DEFAULT = 3

    def __init__(self):
        pass  # Stateless: el historial se pasa como parámetro

    def evaluate(
        self,
        local_synthesis: str,
        cloud_synthesis: str,
        round_number: int,
        max_rounds: int = MAX_ROUNDS_DEFAULT,
        tribunal_verdict: dict | None = None,
        previous_syntheses: list[tuple[str, str]] | None = None,
    ) -> ConvergenceResult:
        """
        Evalúa convergencia entre síntesis local y cloud.
        Retorna recomendación de continuar o detener.
        """
        logger.info(
            "convergence.evaluating",
            round_number=round_number,
            max_rounds=max_rounds,
        )

        # Calcular similitud temática
        similarity = self._calculate_similarity(local_synthesis, cloud_synthesis)

        # Extraer puntos clave
        local_points = self._extract_key_points(local_synthesis)
        cloud_points = self._extract_key_points(cloud_synthesis)

        # Calcular acuerdo en puntos clave
        agreement_ratio = self._calculate_point_agreement(local_points, cloud_points)

        # Detectar áreas de disenso
        dissent_areas = self._identify_dissent_areas(local_synthesis, cloud_synthesis, local_points, cloud_points)

        # Evaluar estabilidad con rondas previas
        stability_score = self._evaluate_stability(local_synthesis, cloud_synthesis, previous_syntheses or [])

        # Calcular score compuesto
        composite_score = similarity * 0.4 + agreement_ratio * 0.3 + stability_score * 0.3

        # Determinar nivel de consenso
        if composite_score >= self.SIMILARITY_THRESHOLD:
            consensus_level = "CONSENSUS_REACHED"
            consensus_reached = True
        elif composite_score >= self.PARTIAL_THRESHOLD:
            consensus_level = "PARTIAL_CONSENSUS"
            consensus_reached = False
        else:
            consensus_level = "DIVERGENT"
            consensus_reached = False

        # ¿Detener o continuar?
        should_stop = self._should_stop(
            consensus_reached=consensus_reached,
            consensus_level=consensus_level,
            round_number=round_number,
            max_rounds=max_rounds,
            stability_score=stability_score,
        )

        # Generar focus para siguiente ronda si continúa
        focus_next = None
        if not should_stop and dissent_areas:
            focus_next = self._generate_focus(dissent_areas, round_number)

        # No almacenar estado: el caller gestiona el historial

        detail = {
            "similarity_score": round(similarity, 3),
            "agreement_ratio": round(agreement_ratio, 3),
            "stability_score": round(stability_score, 3),
            "composite_score": round(composite_score, 3),
            "local_key_points": local_points[:5],
            "cloud_key_points": cloud_points[:5],
            "dissent_areas": dissent_areas[:3] if dissent_areas else [],
        }

        logger.info(
            "convergence.result",
            round_number=round_number,
            consensus_level=consensus_level,
            composite_score=round(composite_score, 3),
            should_stop=should_stop,
        )

        return ConvergenceResult(
            consensus_reached=consensus_reached,
            consensus_level=consensus_level,
            similarity_score=composite_score,
            should_stop=should_stop,
            focus_for_next_round=focus_next,
            detail=detail,
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula similitud semántica simple entre textos.
        Usa overlap de términos clave como heurística.
        """
        if not text1 or not text2:
            return 0.0

        # Extraer términos significativos (palabras de >4 caracteres)
        def extract_terms(text: str) -> set:
            words = re.findall(r"\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]{4,}\b", text.lower())
            # Filtrar stopwords comunes
            stopwords = {
                "este",
                "esta",
                "esto",
                "para",
                "como",
                "pero",
                "son",
                "con",
                "por",
                "los",
                "las",
                "una",
                "del",
                "sido",
            }
            return set(w for w in words if w not in stopwords)

        terms1 = extract_terms(text1)
        terms2 = extract_terms(text2)

        if not terms1 or not terms2:
            return 0.0

        # Jaccard similarity
        intersection = len(terms1 & terms2)
        union = len(terms1 | terms2)

        return intersection / union if union > 0 else 0.0

    def _extract_key_points(self, text: str) -> list[str]:
        """Extrae puntos clave del texto (líneas con bullets o numeración)"""
        if not text:
            return []

        points = []

        # Buscar líneas que empiezan con -, *, número, o ##
        patterns = [
            r"^[\s]*[-*][\s]+(.+)$",
            r"^[\s]*\d+\.[\s]+(.+)$",
            r"^##[\s]*(.+)$",
        ]

        for line in text.split("\n"):
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    point = match.group(1).strip()
                    if len(point) > 10:  # Ignorar líneas muy cortas
                        points.append(point[:100])  # Truncar puntos largos
                    break

        return points

    def _calculate_point_agreement(self, local_points: list[str], cloud_points: list[str]) -> float:
        """Calcula ratio de acuerdo entre puntos clave"""
        if not local_points or not cloud_points:
            return 0.0

        # Contar puntos similares (heurística simple)
        matches = 0
        for lp in local_points:
            lp_lower = lp.lower()
            for cp in cloud_points:
                # Si comparten palabras significativas
                cp_lower = cp.lower()
                lp_words = set(lp_lower.split())
                cp_words = set(cp_lower.split())

                if len(lp_words) > 0:
                    overlap = len(lp_words & cp_words) / len(lp_words)
                    if overlap > 0.5:  # 50% de palabras en común
                        matches += 1
                        break

        max_points = max(len(local_points), len(cloud_points))
        return matches / max_points if max_points > 0 else 0.0

    def _identify_dissent_areas(
        self,
        local_synthesis: str,
        cloud_synthesis: str,
        local_points: list[str],
        cloud_points: list[str],
    ) -> list[str]:
        """Identifica áreas donde hay disenso explícito"""
        dissent = []

        # Buscar secciones de disenso o incertidumbre
        dissent_patterns = [
            r"##?\s*Disenso",
            r"##?\s*Disentimiento",
            r"##?\s*Divergencia",
            r"##?\s*Áreas de Incertidumbre",
            r"##?\s*Desacuerdo",
        ]

        for text in [local_synthesis, cloud_synthesis]:
            for pattern in dissent_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Extraer contenido hasta siguiente ##
                    start = match.start()
                    rest = text[start:]
                    next_section = rest.find("\n##", 10)
                    section_content = rest if next_section == -1 else rest[:next_section]

                    if len(section_content) > 20:
                        dissent.append(section_content[:200].strip())

        # Si no hay secciones explícitas, inferir de puntos no coincidentes
        if not dissent and local_points and cloud_points:
            local_set = set(p.lower()[:30] for p in local_points)
            cloud_set = set(p.lower()[:30] for p in cloud_points)

            unique_local = local_set - cloud_set
            unique_cloud = cloud_set - local_set

            if unique_local:
                dissent.append(f"Local argumenta: {list(unique_local)[0]}...")
            if unique_cloud:
                dissent.append(f"Cloud argumenta: {list(unique_cloud)[0]}...")

        return dissent[:3]  # Limitar a 3 áreas principales

    def _evaluate_stability(
        self,
        current_local: str,
        current_cloud: str,
        previous_syntheses: list[tuple[str, str]],
    ) -> float:
        """Evalúa estabilidad respecto a rondas previas"""
        if not previous_syntheses:
            return 0.5  # Neutral en primera ronda

        # Comparar con ronda anterior
        prev_local, prev_cloud = previous_syntheses[-1]

        local_sim = self._calculate_similarity(current_local, prev_local)
        cloud_sim = self._calculate_similarity(current_cloud, prev_cloud)

        # Promedio de estabilidad
        return (local_sim + cloud_sim) / 2

    def _should_stop(
        self,
        consensus_reached: bool,
        consensus_level: str,
        round_number: int,
        max_rounds: int,
        stability_score: float,
    ) -> bool:
        """
        Determina si se debe detener el debate.
        """
        # Siempre detener si se alcanzó consenso completo
        if consensus_reached:
            return True

        # Detener si se alcanzó máximo de rondas
        if round_number >= max_rounds:
            return True

        # Detener si hay alta estabilidad entre rondas (convergencia implícita)
        if stability_score > 0.85 and consensus_level == "PARTIAL_CONSENSUS":
            return True

        # Continuar en otros casos
        return False

    def _generate_focus(self, dissent_areas: list[str], round_number: int) -> str:
        """Genera instrucciones de foco para siguiente ronda"""
        if not dissent_areas:
            return "Profundizar en aspectos no resueltos"

        # Priorizar áreas principales de disenso
        focus = f"Ronda {round_number + 1}: Centrarse específicamente en:\n"

        for i, area in enumerate(dissent_areas[:2], 1):
            # Limpiar y resumir
            cleaned = area.replace("\n", " ")[:100]
            focus += f"{i}. {cleaned}...\n"

        focus += "\nObjetivo: Alcanzar acuerdo explícito sobre estos puntos."

        return focus
