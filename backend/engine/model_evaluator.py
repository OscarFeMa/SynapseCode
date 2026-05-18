"""
Synapse Council v2.8 - Model Evaluator
Fetches live model rankings from web sources to keep registry updated.
"""

from datetime import datetime, timedelta

import structlog

from .model_registry import ModelRegistry, Specialty, model_registry

logger = structlog.get_logger()

# Cache duration: 6 hours
CACHE_TTL = timedelta(hours=6)


class ModelEvaluator:
    """
    Consulta fuentes web para obtener rankings actualizados de modelos.
    Fuentes principales:
    - LMSYS Chatbot Arena (arena.lmsys.org)
    - OpenRouter stats (openrouter.ai/stats)
    - Artificial Analysis (artificialanalysis.ai)
    """

    def __init__(self, registry: ModelRegistry | None = None):
        self.registry = registry or model_registry
        self._last_fetch: datetime | None = None
        self._lmsys_data: dict[str, dict] = {}
        self._openrouter_data: dict[str, dict] = {}
        self._cache_valid_until: datetime | None = None

    def is_cache_valid(self) -> bool:
        """Verifica si el cache esta vigente"""
        if self._cache_valid_until is None:
            return False
        return datetime.now() < self._cache_valid_until

    async def fetch_lmsys_rankings(self) -> dict[str, dict]:
        """
        Obtiene rankings de LMSYS Chatbot Arena.
        Fuente: https://arena.lmsys.org
        """
        if self.is_cache_valid() and self._lmsys_data:
            return self._lmsys_data

        try:
            # LMSYS publica datos en formato JSON
            # URL oficial del leaderboard
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                # Datos del leaderboard publico
                resp = await client.get(
                    "https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard/resolve/main/leaderboard.json"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._parse_lmsys_data(data)
                    self._cache_valid_until = datetime.now() + CACHE_TTL
                    logger.info("LMSYS rankings fetched successfully")
                else:
                    logger.warning(f"LMSYS fetch failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to fetch LMSYS rankings: {e}")
            # Fallback: usar datos hardcodeados basados en ultimo ranking conocido
            self._lmsys_data = self._get_fallback_lmsys_rankings()

        return self._lmsys_data

    def _parse_lmsys_data(self, data: dict | list):
        """Parsea datos de LMSYS y actualiza registry"""
        # LMSYS devuelve lista de modelos con arena_score
        entries = data if isinstance(data, list) else data.get("data", [])

        for entry in entries:
            model_name = entry.get("model", entry.get("name", ""))
            arena_score = entry.get("arena_rating", entry.get("score", 0))

            # Buscar modelo en registry por nombre similar
            for model_id, spec in self.registry._models.items():
                if self._names_match(model_name, spec.name):
                    spec.lmsys_rank = int(arena_score) if arena_score else 0
                    break

    def _names_match(self, lmsys_name: str, spec_name: str) -> bool:
        """Compara nombres de modelos de forma fuzzy"""
        lmsys_lower = lmsys_name.lower()
        spec_lower = spec_name.lower()

        # Matching directo
        if spec_lower in lmsys_lower or lmsys_lower in spec_lower:
            return True

        # Matching por familia
        if "claude" in lmsys_lower and "claude" in spec_lower:
            return True
        if "gpt" in lmsys_lower and "gpt" in spec_lower:
            return True
        if "gemma" in lmsys_lower and "gemma" in spec_lower:
            return True
        if "llama" in lmsys_lower and "llama" in spec_lower:
            return True
        if "qwen" in lmsys_lower and "qwen" in spec_lower:
            return True
        if "mistral" in lmsys_lower and "mistral" in spec_lower:
            return True

        return False

    def _get_fallback_lmsys_rankings(self) -> dict[str, dict]:
        """
        Rankings fallback basados en ultimo LMSYS conocido (Mayo 2026).
        Se usa cuando no se puede acceder a la API.
        """
        return {
            "claude-sonnet-4": {"rank": 1, "score": 1280, "category": "overall"},
            "gpt-4.1": {"rank": 2, "score": 1270, "category": "overall"},
            "gemini-2.5-pro": {"rank": 3, "score": 1260, "category": "overall"},
            "claude-3.5-sonnet": {"rank": 4, "score": 1240, "category": "overall"},
            "gemini-2.0-flash": {"rank": 5, "score": 1200, "category": "overall"},
            "deepseek-v3": {"rank": 8, "score": 1160, "category": "overall"},
            "llama-3.3-70b": {"rank": 15, "score": 1100, "category": "overall"},
            "qwen2.5-72b": {"rank": 18, "score": 1080, "category": "overall"},
            "gemma-4-26b": {"rank": 25, "score": 1020, "category": "overall"},
            "mixtral-8x7b": {"rank": 35, "score": 950, "category": "overall"},
            "llama-3-8b": {"rank": 50, "score": 880, "category": "overall"},
            "mistral-7b": {"rank": 60, "score": 840, "category": "overall"},
            "qwen2.5-7b": {"rank": 45, "score": 890, "category": "overall"},
            "gemma-7b": {"rank": 55, "score": 860, "category": "overall"},
        }

    async def fetch_openrouter_stats(self) -> dict[str, dict]:
        """
        Obtiene estadisticas de OpenRouter (latencia, throughput, disponibilidad).
        Fuente: https://openrouter.ai/stats
        """
        if self.is_cache_valid() and self._openrouter_data:
            return self._openrouter_data

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://openrouter.ai/api/v1/stats")
                if resp.status_code == 200:
                    data = resp.json()
                    self._parse_openrouter_stats(data)
                    self._cache_valid_until = datetime.now() + CACHE_TTL
                    logger.info("OpenRouter stats fetched successfully")
                else:
                    logger.warning(f"OpenRouter stats fetch failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter stats: {e}")
            self._openrouter_data = self._get_fallback_openrouter_stats()

        return self._openrouter_data

    def _parse_openrouter_stats(self, data: dict):
        """Parsea estadisticas de OpenRouter"""
        for model_id, stats in data.get("models", {}).items():
            if model_id in self.registry._models:
                spec = self.registry._models[model_id]
                # Actualizar velocidad si hay datos reales
                if "throughput" in stats:
                    spec.speed_tps = stats["throughput"]
                if "latency" in stats:
                    pass  # Podria usarse para scoring

    def _get_fallback_openrouter_stats(self) -> dict[str, dict]:
        """Estadisticas fallback de OpenRouter"""
        return {
            "deepseek/deepseek-v4-flash:free": {
                "throughput": 80,
                "latency_ms": 1200,
                "uptime": 0.95,
            },
            "google/gemma-4-26b-a4b-it:free": {
                "throughput": 120,
                "latency_ms": 800,
                "uptime": 0.92,
            },
            "anthropic/claude-sonnet-4-20250514": {
                "throughput": 100,
                "latency_ms": 900,
                "uptime": 0.99,
            },
        }

    async def update_all_rankings(self) -> dict:
        """Actualiza todos los rankings desde fuentes web"""
        lmsys = await self.fetch_lmsys_rankings()
        openrouter = await self.fetch_openrouter_stats()

        self._last_fetch = datetime.now()

        return {
            "status": "updated",
            "last_fetch": self._last_fetch.isoformat(),
            "lmsys_models": len(lmsys),
            "openrouter_models": len(openrouter),
        }

    def get_best_models_by_category(self) -> dict[str, list[str]]:
        """
        Retorna los mejores modelos por categoria basado en rankings.
        """
        categories = {
            "finance": Specialty.FINANCE,
            "coding": Specialty.CODING,
            "analysis": Specialty.ANALYSIS,
            "reasoning": Specialty.REASONING,
            "creative": Specialty.CREATIVE,
            "multilingual": Specialty.MULTILINGUAL,
            "long_context": Specialty.LONG_CONTEXT,
            "fast": Specialty.FAST,
            "free": Specialty.FREE,
        }

        result = {}
        for cat_name, specialty in categories.items():
            models = self.registry.get_models_by_specialty(specialty)
            # Ordenar por LMSYS rank (mayor = mejor)
            models.sort(key=lambda m: m.lmsys_rank, reverse=True)
            result[cat_name] = [m.id for m in models[:5]]  # Top 5

        return result

    def get_model_comparison_table(self) -> list[dict]:
        """Genera tabla comparativa de todos los modelos"""
        table = []
        for spec in self.registry._models.values():
            table.append(
                {
                    "id": spec.id,
                    "name": spec.name,
                    "platform": spec.platform.value,
                    "params_b": spec.params_b,
                    "context_window": spec.context_window,
                    "speed_tps": spec.speed_tps,
                    "lmsys_rank": spec.lmsys_rank,
                    "is_free": spec.is_free,
                    "cost_input": spec.cost_per_1m_input,
                    "cost_output": spec.cost_per_1m_output,
                    "specialties": [s.value for s in spec.specialties],
                }
            )
        # Ordenar por LMSYS rank
        table.sort(key=lambda x: x["lmsys_rank"], reverse=True)
        return table


# Singleton global
model_evaluator = ModelEvaluator()
