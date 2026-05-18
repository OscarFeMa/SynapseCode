"""
Synapse Council v2.8 - Role Matcher
Intelligent model-to-role assignment based on capabilities, platform, and workflow.
"""

from dataclasses import dataclass

import structlog

from .model_evaluator import ModelEvaluator, model_evaluator
from .model_registry import ModelRegistry, ModelSpec, Platform, Specialty, model_registry

logger = structlog.get_logger()


@dataclass
class RoleAssignment:
    """Asignacion de modelo a un rol especifico"""
    role: str
    model_id: str
    model_name: str
    platform: str
    node: str  # CLOUD o LOCAL
    reason: str
    expected_quality: float  # 0-100
    expected_latency_ms: int


class RoleMatcher:
    """
    Asigna el mejor modelo disponible a cada rol considerando:
    - Especialidad del modelo vs requisitos del rol
    - Plataforma disponible (Cloud vs Local)
    - Contexto necesario
    - Velocidad requerida
    - Restricciones de costo
    - VRAM disponible (para modelos locales)
    """

    # Definicion de roles y sus requisitos
    ROLE_REQUIREMENTS = {
        "analyst": {
            "primary_specialty": Specialty.ANALYSIS,
            "secondary_specialties": [Specialty.REASONING, Specialty.FINANCE],
            "min_context": 8000,
            "preferred_platform": Platform.OPENROUTER,
            "quality_weight": 0.8,
            "speed_weight": 0.2,
            "description": "Analisis profundo, identificacion de patrones",
        },
        "critic": {
            "primary_specialty": Specialty.REASONING,
            "secondary_specialties": [Specialty.ANALYSIS, Specialty.GENERAL],
            "min_context": 8000,
            "preferred_platform": Platform.OPENROUTER,
            "quality_weight": 0.7,
            "speed_weight": 0.3,
            "description": "Pensamiento critico, deteccion de falacias",
        },
        "synthesizer": {
            "primary_specialty": Specialty.GENERAL,
            "secondary_specialties": [Specialty.MULTILINGUAL, Specialty.CREATIVE],
            "min_context": 12000,
            "preferred_platform": Platform.OPENROUTER,
            "quality_weight": 0.6,
            "speed_weight": 0.4,
            "description": "Sintesis de argumentos, integracion de perspectivas",
        },
        "refiner": {
            "primary_specialty": Specialty.REASONING,
            "secondary_specialties": [Specialty.ANALYSIS, Specialty.CODING],
            "min_context": 8000,
            "preferred_platform": Platform.OPENROUTER,
            "quality_weight": 0.9,
            "speed_weight": 0.1,
            "description": "Refinamiento de alta calidad, precision",
        },
        "validator": {
            "primary_specialty": Specialty.REASONING,
            "secondary_specialties": [Specialty.MATH, Specialty.ANALYSIS],
            "min_context": 4000,
            "preferred_platform": Platform.OPENROUTER,
            "quality_weight": 0.9,
            "speed_weight": 0.1,
            "description": "Validacion logica, verificacion de consistencia",
        },
        "moderator": {
            "primary_specialty": Specialty.GENERAL,
            "secondary_specialties": [Specialty.CREATIVE, Specialty.MULTILINGUAL],
            "min_context": 8000,
            "preferred_platform": Platform.OPENROUTER,
            "quality_weight": 0.5,
            "speed_weight": 0.5,
            "description": "Moderacion, resumen, consenso",
        },
        "coder": {
            "primary_specialty": Specialty.CODING,
            "secondary_specialties": [Specialty.ANALYSIS, Specialty.REASONING],
            "min_context": 16000,
            "preferred_platform": Platform.OPENROUTER,
            "quality_weight": 0.8,
            "speed_weight": 0.2,
            "description": "Generacion y revision de codigo",
        },
        "researcher": {
            "primary_specialty": Specialty.ANALYSIS,
            "secondary_specialties": [Specialty.MULTILINGUAL, Specialty.LONG_CONTEXT],
            "min_context": 32000,
            "preferred_platform": Platform.OPENROUTER,
            "quality_weight": 0.7,
            "speed_weight": 0.3,
            "description": "Investigacion, revision de literatura",
        },
    }

    # VRAM disponible en Worker (GB)
    WORKER_VRAM_GB = 13.5

    # Modelos que causan OOM en Worker
    OOM_MODELS = {"qwen2.5-coder:14b", "qwen2.5:14b", "llama3:70b", "mixtral:8x7b"}

    def __init__(self, registry: ModelRegistry | None = None, evaluator: ModelEvaluator | None = None):
        self.registry = registry or model_registry
        self.evaluator = evaluator or model_evaluator

    def match_role_to_model(
        self,
        role: str,
        platform: Platform | None = None,
        require_free: bool = True,
        min_context: int = 0,
        max_vram_gb: float = WORKER_VRAM_GB,
    ) -> RoleAssignment | None:
        """
        Encuentra el mejor modelo para un rol dado.
        """
        requirements = self.ROLE_REQUIREMENTS.get(role)
        if not requirements:
            logger.warning(f"Unknown role: {role}")
            return None

        # Obtener candidatos
        candidates = self._get_candidates(
            role=role,
            platform=platform,
            require_free=require_free,
            min_context=max(min_context, requirements["min_context"]),
            max_vram_gb=max_vram_gb,
        )

        if not candidates:
            logger.error(f"No candidates found for role: {role}")
            return None

        # Scoring
        scored = []
        for model in candidates:
            score = self._score_model_for_role(model, requirements)
            scored.append((model, score))

        # Ordenar por score descendente
        scored.sort(key=lambda x: x[1], reverse=True)
        best_model, best_score = scored[0]

        # Calcular calidad esperada (0-100)
        expected_quality = min(best_score * 20, 100)

        # Calcular latencia esperada
        if best_model.speed_tps > 0:
            expected_latency_ms = int(500 / best_model.speed_tps * 1000)  # ~500 tokens
        else:
            expected_latency_ms = 5000

        # Determinar nodo
        node = "CLOUD" if best_model.platform == Platform.OPENROUTER else "LOCAL"

        return RoleAssignment(
            role=role,
            model_id=best_model.id,
            model_name=best_model.name,
            platform=best_model.platform.value,
            node=node,
            reason=self._explain_assignment(best_model, requirements),
            expected_quality=round(expected_quality, 1),
            expected_latency_ms=expected_latency_ms,
        )

    def match_all_roles(
        self,
        roles: list[str] | None = None,
        platform: Platform | None = None,
        require_free: bool = True,
    ) -> list[RoleAssignment]:
        """Asigna modelos a todos los roles especificados"""
        if roles is None:
            roles = list(self.ROLE_REQUIREMENTS.keys())

        assignments = []
        for role in roles:
            assignment = self.match_role_to_model(
                role=role, platform=platform, require_free=require_free
            )
            if assignment:
                assignments.append(assignment)

        return assignments

    def generate_debate_config(
        self,
        topic: str,
        max_turns: int = 6,
        mode: str = "hybrid_rotation",
    ) -> list[dict]:
        """
        Genera configuracion completa de debate con asignacion inteligente.
        """
        # Roles en orden de debate
        debate_roles = ["analyst", "critic", "synthesizer", "refiner", "validator", "moderator"]
        debate_roles = debate_roles[:max_turns]

        agents = []
        last_platform = None

        for i, role in enumerate(debate_roles):
            if mode == "hybrid_rotation":
                # NUNCA dos turnos consecutivos con OpenRouter
                if last_platform == Platform.OPENROUTER:
                    platform = Platform.OLLAMA
                elif i in (0, 3):  # Turnos clave van a Cloud
                    platform = Platform.OPENROUTER
                else:
                    platform = Platform.OLLAMA
            elif mode == "cloud_only":
                platform = Platform.OPENROUTER
            elif mode == "local_only":
                platform = Platform.OLLAMA
            else:
                platform = None

            assignment = self.match_role_to_model(role=role, platform=platform, require_free=True)

            if assignment:
                last_platform = Platform(assignment.platform)
                agents.append({
                    "id": f"{role}_{assignment.platform}",
                    "name": assignment.model_name,
                    "role": role,
                    "node": assignment.node,
                    "engine": assignment.platform,
                    "model": assignment.model_id,
                    "reason": assignment.reason,
                    "expected_quality": assignment.expected_quality,
                    "expected_latency_ms": assignment.expected_latency_ms,
                    "system_prompt": self._get_system_prompt(role, topic),
                    "temperature": self._get_temperature(role),
                    "max_tokens": self._get_max_tokens(role),
                })

        return agents

    def _get_candidates(
        self,
        role: str,
        platform: Platform | None = None,
        require_free: bool = True,
        min_context: int = 0,
        max_vram_gb: float = WORKER_VRAM_GB,
    ) -> list[ModelSpec]:
        """Obtiene modelos candidatos filtrados"""
        requirements = self.ROLE_REQUIREMENTS[role]

        # Obtener modelos por especialidad primaria
        candidates = self.registry.get_models_by_specialty(requirements["primary_specialty"])

        # Tambien incluir modelos con especialidades secundarias
        for spec in self.registry.get_models_by_specialty(Specialty.GENERAL):
            if spec not in candidates:
                candidates.append(spec)

        # Filtrar por plataforma
        if platform:
            candidates = [m for m in candidates if m.platform == platform]

        # Filtrar por costo
        if require_free:
            candidates = [m for m in candidates if m.is_free]

        # Filtrar por contexto minimo
        if min_context > 0:
            candidates = [m for m in candidates if m.context_window >= min_context]

        # Filtrar modelos OOM para Worker
        if platform == Platform.OLLAMA:
            candidates = [
                m for m in candidates
                if m.ollama_model not in self.OOM_MODELS
                and m.id not in self.OOM_MODELS
            ]

        # Filtrar por VRAM (estimado: 2GB por billon de params)
        if platform == Platform.OLLAMA:
            candidates = [
                m for m in candidates
                if (m.params_b * 2) <= max_vram_gb
            ]

        return candidates

    def _score_model_for_role(self, model: ModelSpec, requirements: dict) -> float:
        """
        Score un modelo para un rol especifico.
        """
        score = 0.0

        # Specialty match (0-40 puntos)
        if requirements["primary_specialty"] in model.specialties:
            score += 40
        for spec in requirements["secondary_specialties"]:
            if spec in model.specialties:
                score += 10

        # Context bonus (0-20 puntos)
        context_ratio = min(model.context_window / requirements["min_context"], 2.0)
        score += context_ratio * 10

        # Speed bonus (0-15 puntos)
        if model.speed_tps > 0:
            speed_ratio = min(model.speed_tps / 100, 1.0)
            score += speed_ratio * 15

        # LMSYS rank bonus (0-25 puntos)
        if model.lmsys_rank > 0:
            rank_ratio = min(model.lmsys_rank / 1300, 1.0)
            score += rank_ratio * 25

        # Quality vs Speed weight
        quality_weight = requirements.get("quality_weight", 0.5)
        speed_weight = requirements.get("speed_weight", 0.5)
        final_score = score * (quality_weight + speed_weight * 0.5)

        return final_score

    def _explain_assignment(self, model: ModelSpec, requirements: dict) -> str:
        """Explica por que se asigno este modelo"""
        reasons = []

        if requirements["primary_specialty"] in model.specialties:
            reasons.append(f"Especialista en {requirements['primary_specialty'].value}")

        if model.is_free:
            reasons.append("Gratuito")

        if model.context_window >= 32000:
            reasons.append(f"Contexto grande ({model.context_window // 1000}k)")

        if model.speed_tps >= 80:
            reasons.append(f"Rapido ({model.speed_tps} tps)")

        if model.lmsys_rank > 1100:
            reasons.append(f"Top LMSYS (score: {model.lmsys_rank})")

        return ", ".join(reasons) if reasons else "Mejor disponible"

    def _get_system_prompt(self, role: str, topic: str) -> str:
        """Prompt por rol"""
        prompts = {
            "analyst": "Analiza el tema propuesto desde una perspectiva tecnica y estructurada. Identifica los puntos clave, supuestos y posibles enfoques. Responde en espanol, maximo 500 palabras.",
            "critic": "Examina criticamente el analisis anterior. Identifica debilidades logicas, supuestos no verificados y alternativas no consideradas. Se constructivo pero riguroso. Responde en espanol, maximo 500 palabras.",
            "synthesizer": "Sintetiza los argumentos presentados hasta ahora. Encuentra puntos de acuerdo y desacuerdo. Propone un marco integrador. Responde en espanol, maximo 500 palabras.",
            "refiner": "Refina y mejora la sintesis anterior. Considera perspectivas adicionales y elabora una conclusion bien fundamentada. Responde en espanol, maximo 600 palabras.",
            "validator": "Valida la solidez logica de todos los argumentos presentados. Verifica consistencia interna y externa. Responde en espanol, maximo 400 palabras.",
            "moderator": "Modera el debate, resume las posiciones encontradas y propone areas de consenso. Responde en espanol, maximo 500 palabras.",
            "coder": "Genera, revisa o mejora codigo relacionado con el tema. Explica tus decisiones tecnicas. Responde en espanol.",
            "researcher": "Investiga el tema propuesto. Proporciona contexto, antecedentes y perspectivas diversas. Responde en espanol, maximo 600 palabras.",
        }
        return prompts.get(role, prompts["analyst"])

    def _get_temperature(self, role: str) -> float:
        temps = {
            "analyst": 0.7,
            "critic": 0.8,
            "synthesizer": 0.6,
            "refiner": 0.5,
            "validator": 0.4,
            "moderator": 0.6,
            "coder": 0.3,
            "researcher": 0.7,
        }
        return temps.get(role, 0.7)

    def _get_max_tokens(self, role: str) -> int:
        tokens = {
            "analyst": 1000,
            "critic": 1000,
            "synthesizer": 1000,
            "refiner": 1200,
            "validator": 800,
            "moderator": 1000,
            "coder": 2000,
            "researcher": 1500,
        }
        return tokens.get(role, 1000)


# Singleton global
role_matcher = RoleMatcher()
