"""
Synapse Council v2.8 - Model Registry & Evaluation System
Dynamic model registry with live rankings, role matching, and platform awareness.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class Platform(str, Enum):
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    GROQ = "groq"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    LM_STUDIO = "lm_studio"
    JAN = "jan"


class Specialty(str, Enum):
    GENERAL = "general"
    FINANCE = "finance"
    CODING = "coding"
    ANALYSIS = "analysis"
    REASONING = "reasoning"
    CREATIVE = "creative"
    MATH = "math"
    MULTILINGUAL = "multilingual"
    LONG_CONTEXT = "long_context"
    FAST = "fast"
    CHEAP = "cheap"
    FREE = "free"


@dataclass
class ModelSpec:
    """Especificaciones de un modelo"""

    id: str  # OpenRouter ID o nombre Ollama
    name: str
    platform: Platform
    provider: str
    params_b: float  # Billones de parametros
    context_window: int  # Tokens maximos
    speed_tps: float = 0  # Tokens por segundo (estimado)
    cost_per_1m_input: float = 0  # USD
    cost_per_1m_output: float = 0
    is_free: bool = False
    specialties: list[Specialty] = field(default_factory=list)
    lmsys_rank: int = 0  # Arena ranking
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    ollama_model: str = ""  # Nombre en Ollama si aplica
    last_updated: datetime = field(default_factory=datetime.now)


class ModelRegistry:
    """
    Registro central de modelos disponibles con metadata dinamica.
    Se actualiza periodicamente desde fuentes web.
    """

    def __init__(self):
        self._models: dict[str, ModelSpec] = {}
        self._role_preferences: dict[str, list[str]] = {}
        self._last_fetch: datetime | None = None
        self._initialize_known_models()

    def _initialize_known_models(self):
        """Inicializa con modelos conocidos (base para actualizacion web)"""
        models = [
            # OpenRouter - Free Tier
            ModelSpec(
                id="deepseek/deepseek-v4-flash:free",
                name="DeepSeek V4 Flash",
                platform=Platform.OPENROUTER,
                provider="deepseek",
                params_b=671,
                context_window=128000,
                speed_tps=80,
                is_free=True,
                specialties=[Specialty.GENERAL, Specialty.ANALYSIS, Specialty.FREE],
                strengths=["MoE architecture", "Strong reasoning", "Free tier", "Large context"],
                weaknesses=["Rate limited", "May be slow during peak"],
            ),
            ModelSpec(
                id="google/gemma-4-26b-a4b-it:free",
                name="Gemma 4 26B",
                platform=Platform.OPENROUTER,
                provider="google",
                params_b=26,
                context_window=32000,
                speed_tps=120,
                is_free=True,
                specialties=[Specialty.GENERAL, Specialty.CREATIVE, Specialty.FREE],
                strengths=["Google quality", "Good instruction following", "Free"],
                weaknesses=["Rate limited", "Smaller context"],
            ),
            ModelSpec(
                id="google/gemma-4-31b-it:free",
                name="Gemma 4 31B",
                platform=Platform.OPENROUTER,
                provider="google",
                params_b=31,
                context_window=32000,
                speed_tps=100,
                is_free=True,
                specialties=[Specialty.ANALYSIS, Specialty.REASONING, Specialty.FREE],
                strengths=["Larger Gemma", "Better reasoning", "Free"],
                weaknesses=["Rate limited"],
            ),
            ModelSpec(
                id="minimax/minimax-m2.5:free",
                name="MiniMax M2.5",
                platform=Platform.OPENROUTER,
                provider="minimax",
                params_b=100,
                context_window=245000,
                speed_tps=60,
                is_free=True,
                specialties=[Specialty.LONG_CONTEXT, Specialty.CREATIVE, Specialty.FREE],
                strengths=["Huge context window", "Good for long documents", "Free"],
                weaknesses=["Less known", "Rate limited"],
            ),
            ModelSpec(
                id="nvidia/nemotron-3-super-120b-a12b:free",
                name="Nemotron 3 Super 120B",
                platform=Platform.OPENROUTER,
                provider="nvidia",
                params_b=120,
                context_window=128000,
                speed_tps=40,
                is_free=True,
                specialties=[Specialty.ANALYSIS, Specialty.REASONING, Specialty.FREE],
                strengths=["Large model", "NVIDIA quality", "Free"],
                weaknesses=["Slower", "Rate limited"],
            ),
            # OpenRouter - Paid (high quality)
            ModelSpec(
                id="anthropic/claude-sonnet-4-20250514",
                name="Claude Sonnet 4",
                platform=Platform.OPENROUTER,
                provider="anthropic",
                params_b=0,
                context_window=200000,
                speed_tps=100,
                cost_per_1m_input=3.0,
                cost_per_1m_output=15.0,
                specialties=[Specialty.ANALYSIS, Specialty.REASONING, Specialty.CODING, Specialty.FINANCE],
                strengths=["Excellent reasoning", "Great for finance", "Long context", "Strong analysis"],
                weaknesses=["Paid", "Expensive for long debates"],
            ),
            ModelSpec(
                id="openai/gpt-4.1",
                name="GPT-4.1",
                platform=Platform.OPENROUTER,
                provider="openai",
                params_b=0,
                context_window=1047576,
                speed_tps=80,
                cost_per_1m_input=2.0,
                cost_per_1m_output=8.0,
                specialties=[Specialty.GENERAL, Specialty.ANALYSIS, Specialty.FINANCE, Specialty.LONG_CONTEXT],
                strengths=["Huge context", "Excellent generalist", "Good for finance"],
                weaknesses=["Paid", "Expensive"],
            ),
            ModelSpec(
                id="google/gemini-2.5-pro",
                name="Gemini 2.5 Pro",
                platform=Platform.OPENROUTER,
                provider="google",
                params_b=0,
                context_window=1000000,
                speed_tps=60,
                cost_per_1m_input=1.25,
                cost_per_1m_output=10.0,
                specialties=[Specialty.LONG_CONTEXT, Specialty.ANALYSIS, Specialty.MULTILINGUAL],
                strengths=["Massive context", "Multilingual", "Good analysis"],
                weaknesses=["Paid", "Slower"],
            ),
            # Ollama - Local models (Worker)
            ModelSpec(
                id="llama3:8b",
                name="Llama 3 8B",
                platform=Platform.OLLAMA,
                provider="meta",
                params_b=8,
                context_window=8192,
                speed_tps=50,
                is_free=True,
                specialties=[Specialty.GENERAL, Specialty.FAST],
                strengths=["Fast", "Good generalist", "Low VRAM"],
                weaknesses=["Small context", "Limited reasoning"],
                ollama_model="llama3:8b",
            ),
            ModelSpec(
                id="llama3.1:8b",
                name="Llama 3.1 8B",
                platform=Platform.OLLAMA,
                provider="meta",
                params_b=8,
                context_window=128000,
                speed_tps=45,
                is_free=True,
                specialties=[Specialty.GENERAL, Specialty.LONG_CONTEXT],
                strengths=["Long context", "Updated knowledge", "Good generalist"],
                weaknesses=["Slower than 3.0"],
                ollama_model="llama3.1:8b",
            ),
            ModelSpec(
                id="mistral:7b",
                name="Mistral 7B",
                platform=Platform.OLLAMA,
                provider="mistral",
                params_b=7,
                context_window=32000,
                speed_tps=55,
                is_free=True,
                specialties=[Specialty.ANALYSIS, Specialty.FAST],
                strengths=["Good analysis", "Fast", "Efficient"],
                weaknesses=["Smaller than 8B models"],
                ollama_model="mistral:7b",
            ),
            ModelSpec(
                id="qwen2.5:7b",
                name="Qwen 2.5 7B",
                platform=Platform.OLLAMA,
                provider="alibaba",
                params_b=7,
                context_window=32768,
                speed_tps=50,
                is_free=True,
                specialties=[Specialty.MULTILINGUAL, Specialty.ANALYSIS, Specialty.CODING],
                strengths=["Excellent multilingual", "Good coding", "Strong analysis"],
                weaknesses=["Chinese training bias"],
                ollama_model="qwen2.5:7b",
            ),
            ModelSpec(
                id="qwen2.5-coder:7b",
                name="Qwen 2.5 Coder 7B",
                platform=Platform.OLLAMA,
                provider="alibaba",
                params_b=7,
                context_window=32768,
                speed_tps=50,
                is_free=True,
                specialties=[Specialty.CODING, Specialty.ANALYSIS],
                strengths=["Best coding model under 10B", "Good analysis"],
                weaknesses=["Specialized for code"],
                ollama_model="qwen2.5-coder:7b",
            ),
            ModelSpec(
                id="deepseek-r1:7b",
                name="DeepSeek R1 7B",
                platform=Platform.OLLAMA,
                provider="deepseek",
                params_b=7,
                context_window=32768,
                speed_tps=30,
                is_free=True,
                specialties=[Specialty.REASONING, Specialty.MATH],
                strengths=["Chain of thought reasoning", "Good for math"],
                weaknesses=["Slow", "Verbose"],
                ollama_model="deepseek-r1:7b",
            ),
            ModelSpec(
                id="gemma:7b",
                name="Gemma 7B",
                platform=Platform.OLLAMA,
                provider="google",
                params_b=7,
                context_window=8192,
                speed_tps=55,
                is_free=True,
                specialties=[Specialty.CREATIVE, Specialty.GENERAL],
                strengths=["Google quality", "Good creative writing"],
                weaknesses=["Small context"],
                ollama_model="gemma:7b",
            ),
            ModelSpec(
                id="gemma3:4b",
                name="Gemma 3 4B",
                platform=Platform.OLLAMA,
                provider="google",
                params_b=4,
                context_window=32000,
                speed_tps=70,
                is_free=True,
                specialties=[Specialty.FAST, Specialty.GENERAL],
                strengths=["Very fast", "Low VRAM", "Good for its size"],
                weaknesses=["Small model"],
                ollama_model="gemma3:4b",
            ),
            ModelSpec(
                id="gemma4:latest",
                name="Gemma 4",
                platform=Platform.OLLAMA,
                provider="google",
                params_b=0,
                context_window=32000,
                speed_tps=40,
                is_free=True,
                specialties=[Specialty.GENERAL, Specialty.ANALYSIS],
                strengths=["Latest Gemma", "Good quality"],
                weaknesses=["Unknown specs"],
                ollama_model="gemma4:latest",
            ),
            ModelSpec(
                id="phi3:mini",
                name="Phi 3 Mini",
                platform=Platform.OLLAMA,
                provider="microsoft",
                params_b=3.8,
                context_window=128000,
                speed_tps=60,
                is_free=True,
                specialties=[Specialty.FAST, Specialty.LONG_CONTEXT],
                strengths=["Very fast", "Long context for size", "Low VRAM"],
                weaknesses=["Small model", "Limited reasoning"],
                ollama_model="phi3:mini",
            ),
            ModelSpec(
                id="nemotron-mini:latest",
                name="Nemotron Mini",
                platform=Platform.OLLAMA,
                provider="nvidia",
                params_b=0,
                context_window=4096,
                speed_tps=50,
                is_free=True,
                specialties=[Specialty.GENERAL],
                strengths=["NVIDIA quality", "Fast"],
                weaknesses=["Small context", "Unknown specs"],
                ollama_model="nemotron-mini:latest",
            ),
            ModelSpec(
                id="tinyllama:latest",
                name="TinyLlama",
                platform=Platform.OLLAMA,
                provider="meta",
                params_b=1.1,
                context_window=2048,
                speed_tps=100,
                is_free=True,
                specialties=[Specialty.FAST, Specialty.CHEAP],
                strengths=["Extremely fast", "Minimal VRAM"],
                weaknesses=["Very small", "Limited quality"],
                ollama_model="tinyllama:latest",
            ),
            # Groq models
            ModelSpec(
                id="llama-3.3-70b-versatile",
                name="Llama 3.3 70B",
                platform=Platform.GROQ,
                provider="meta",
                params_b=70,
                context_window=128000,
                speed_tps=200,
                specialties=[Specialty.GENERAL, Specialty.ANALYSIS, Specialty.REASONING],
                strengths=["Very fast for 70B", "Excellent quality", "Large context"],
                weaknesses=["Groq rate limits"],
            ),
            ModelSpec(
                id="mixtral-8x7b-32768",
                name="Mixtral 8x7B",
                platform=Platform.GROQ,
                provider="mistral",
                params_b=46.7,
                context_window=32768,
                speed_tps=300,
                specialties=[Specialty.FAST, Specialty.GENERAL],
                strengths=["Extremely fast", "MoE efficiency"],
                weaknesses=["Smaller context", "Groq rate limits"],
            ),
        ]

        for m in models:
            self._models[m.id] = m

        # Role preferences (que tipo de modelo busca cada rol)
        self._role_preferences = {
            "analyst": [Specialty.ANALYSIS, Specialty.REASONING, Specialty.FINANCE],
            "critic": [Specialty.REASONING, Specialty.ANALYSIS, Specialty.GENERAL],
            "synthesizer": [Specialty.GENERAL, Specialty.MULTILINGUAL, Specialty.CREATIVE],
            "refiner": [Specialty.REASONING, Specialty.ANALYSIS, Specialty.CODING],
            "validator": [Specialty.REASONING, Specialty.MATH, Specialty.ANALYSIS],
            "moderator": [Specialty.GENERAL, Specialty.CREATIVE, Specialty.MULTILINGUAL],
        }

    def get_model(self, model_id: str) -> ModelSpec | None:
        """Obtiene especificaciones de un modelo"""
        return self._models.get(model_id)

    def get_models_by_platform(self, platform: Platform) -> list[ModelSpec]:
        """Lista modelos por plataforma"""
        return [m for m in self._models.values() if m.platform == platform]

    def get_models_by_specialty(self, specialty: Specialty) -> list[ModelSpec]:
        """Lista modelos por especialidad"""
        return [m for m in self._models.values() if specialty in m.specialties]

    def get_best_model_for_role(
        self,
        role: str,
        platform: Platform | None = None,
        require_free: bool = False,
        min_context: int = 0,
    ) -> ModelSpec | None:
        """
        Encuentra el mejor modelo para un rol dado.
        Considera especialidad, plataforma, costo y contexto minimo.
        """
        preferences = self._role_preferences.get(role, [Specialty.GENERAL])

        candidates = list(self._models.values())

        # Filtrar por plataforma
        if platform:
            candidates = [m for m in candidates if m.platform == platform]

        # Filtrar por costo
        if require_free:
            candidates = [m for m in candidates if m.is_free]

        # Filtrar por contexto minimo
        if min_context > 0:
            candidates = [m for m in candidates if m.context_window >= min_context]

        if not candidates:
            return None

        # Scoring: priorizar modelos con mas specialties matching
        def score_model(m: ModelSpec) -> float:
            specialty_score = sum(1 for s in preferences if s in m.specialties)
            # Bonus por contexto grande
            context_bonus = min(m.context_window / 100000, 2.0)
            # Bonus por velocidad
            speed_bonus = min(m.speed_tps / 100, 1.0)
            # Penalizacion por costo (si no es free)
            cost_penalty = (m.cost_per_1m_input + m.cost_per_1m_output) / 10 if not m.is_free else 0
            return specialty_score + context_bonus + speed_bonus - cost_penalty

        return max(candidates, key=score_model)

    def get_available_models(self) -> dict[str, list[dict[str, Any]]]:
        """Retorna modelos disponibles agrupados por plataforma"""
        result: dict[str, list[dict[str, Any]]] = {}
        for m in self._models.values():
            platform = m.platform.value
            if platform not in result:
                result[platform] = []
            result[platform].append(
                {
                    "id": m.id,
                    "name": m.name,
                    "params_b": m.params_b,
                    "context_window": m.context_window,
                    "speed_tps": m.speed_tps,
                    "is_free": m.is_free,
                    "cost_input": m.cost_per_1m_input,
                    "cost_output": m.cost_per_1m_output,
                    "specialties": [s.value for s in m.specialties],
                    "strengths": m.strengths,
                    "weaknesses": m.weaknesses,
                }
            )
        return result

    def generate_hybrid_config(self, topic: str, max_turns: int = 6) -> list[dict[str, Any]]:
        """
        Genera configuracion hibrida inteligente:
        - Turnos clave (analyst, synthesizer) -> OpenRouter (mejor calidad)
        - Turnos secundarios -> Ollama Worker (rapido, gratis)
        - NUNCA dos turnos consecutivos con OpenRouter
        """
        agents = []

        # Definir roles en orden
        roles = ["analyst", "critic", "synthesizer", "refiner", "validator", "moderator"]
        roles = roles[:max_turns]

        for i, role in enumerate(roles):
            # Determinar plataforma: OpenRouter solo en turnos 0 y 3 (no consecutivos)
            use_openrouter = i in (0, 3) and i < max_turns

            if use_openrouter:
                model = self.get_best_model_for_role(role, platform=Platform.OPENROUTER, require_free=True)
            else:
                model = self.get_best_model_for_role(role, platform=Platform.OLLAMA, require_free=True)

            if model:
                agents.append(
                    {
                        "id": f"{role}_{model.platform.value}",
                        "name": f"{model.name} ({role.title()})",
                        "role": role,
                        "node": "CLOUD" if model.platform == Platform.OPENROUTER else "LOCAL",
                        "engine": model.platform.value,
                        "model": model.ollama_model if model.platform == Platform.OLLAMA else model.id,
                        "provider": model.provider,
                        "system_prompt": self._get_system_prompt(role, topic),
                        "temperature": self._get_temperature(role),
                        "max_tokens": self._get_max_tokens(role),
                    }
                )

        return agents

    def _get_system_prompt(self, role: str, topic: str) -> str:
        """Prompt por rol"""
        prompts = {
            "analyst": "Analiza el tema propuesto desde una perspectiva tecnica y estructurada. Identifica los puntos clave, supuestos y posibles enfoques. Responde en espanol, maximo 500 palabras.",
            "critic": "Examina criticamente el analisis anterior. Identifica debilidades logicas, supuestos no verificados y alternativas no consideradas. Se constructivo pero riguroso. Responde en espanol, maximo 500 palabras.",
            "synthesizer": "Sintetiza los argumentos presentados hasta ahora. Encuentra puntos de acuerdo y desacuerdo. Propone un marco integrador. Responde en espanol, maximo 500 palabras.",
            "refiner": "Refina y mejora la sintesis anterior. Considera perspectivas adicionales y elabora una conclusion bien fundamentada. Responde en espanol, maximo 600 palabras.",
            "validator": "Valida la solidez logica de todos los argumentos presentados. Verifica consistencia interna y externa. Responde en espanol, maximo 400 palabras.",
            "moderator": "Modera el debate, resume las posiciones encontradas y propone areas de consenso. Responde en espanol, maximo 500 palabras.",
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
        }
        return tokens.get(role, 1000)


# Singleton global
model_registry = ModelRegistry()
