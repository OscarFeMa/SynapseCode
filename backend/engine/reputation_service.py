"""
Synapse Council v2.0 - Reputation Service (Query Layer)
Capa de consulta sobre reputation_unified para obtener scores
y usarlos como coeficientes en tiempo real.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.local_db import AsyncSessionLocal
from backend.database.models import ModelReputation

logger = structlog.get_logger()


@dataclass
class ModelReputationScore:
    """Score de reputación para un modelo+rol"""

    model: str
    provider: str
    role: str
    tsa_score: float = 0.5
    iid_score: float = 0.5
    pvt_score: float = 0.5
    efficiency_score: float = 0.5
    reputation_score: float = 0.5
    total_debates: int = 0
    total_turns: int = 0

    def weight(self) -> float:
        """Peso compuesto para usar como coeficiente"""
        return self.reputation_score


class ReputationQueryService:
    """
    Servicio de consulta de reputación EMA.
    - Carga scores desde SQLite
    - Provee coeficientes para ponderación de respuestas
    - Se integra con reputation_unified para actualizaciones
    """

    def __init__(self):
        self._cache: Dict[str, ModelReputationScore] = {}
        self._loaded = False

    async def _load_cache(self):
        if self._loaded:
            return
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(ModelReputation))
                for row in result.scalars().all():
                    key = f"{row.model}:{row.role}"
                    self._cache[key] = ModelReputationScore(
                        model=row.model,
                        provider=row.provider,
                        role=row.role,
                        tsa_score=row.tsa_score,
                        iid_score=row.iid_score,
                        pvt_score=row.pvt_score,
                        efficiency_score=row.efficiency_score,
                        reputation_score=row.reputation_score,
                        total_debates=row.total_debates,
                        total_turns=row.total_turns,
                    )
            self._loaded = True
            logger.info("reputation.cache_loaded", entries=len(self._cache))
        except Exception as e:
            logger.warning("reputation.cache_load_failed", error=str(e))

    async def get_score(self, model: str, role: str) -> ModelReputationScore:
        """Obtiene score de reputación para modelo+rol"""
        await self._load_cache()
        key = f"{model}:{role}"
        if key in self._cache:
            return self._cache[key]

        # Fallback: buscar solo por modelo (cualquier rol)
        for k, score in self._cache.items():
            if score.model == model:
                return score

        # Default
        return ModelReputationScore(model=model, provider="unknown", role=role)

    async def get_all_scores(self) -> List[ModelReputationScore]:
        """Retorna todos los scores ordenados por reputation_score"""
        await self._load_cache()
        return sorted(self._cache.values(), key=lambda s: s.reputation_score, reverse=True)

    async def get_weighted_response(
        self,
        responses: List[Dict[str, str]],
        models: List[str],
        roles: List[str],
    ) -> Dict[str, float]:
        """
        Calcula pesos para cada respuesta basados en reputación.
        Args:
            responses: lista de respuestas [{slot: text}]
            models: lista de modelos correspondientes
            roles: lista de roles correspondientes
        Returns:
            Dict con {slot: weight} normalizado (suma=1.0)
        """
        weights = []
        for model, role in zip(models, roles):
            score = await self.get_score(model, role)
            weights.append(score.weight())

        total = sum(weights)
        if total == 0:
            total = len(weights)

        normalized = [w / total for w in weights]
        return {f"{m}:{r}": w for (m, r), w in zip(zip(models, roles), normalized)}

    def format_reputation_context(self, scores: List[ModelReputationScore]) -> str:
        """Formatea scores como contexto para prompts del tribunal"""
        if not scores:
            return ""

        lines = ["## Reputación Histórica de Modelos (EMA Scores)"]
        lines.append("| Modelo | Rol | TSA | IID | PVT | Eficiencia | Score | Debates |")
        lines.append("|--------|-----|-----|-----|-----|-----------|-------|---------|")

        for s in scores[:10]:  # Top 10
            lines.append(
                f"| {s.model} | {s.role} | {s.tsa_score:.2f} | {s.iid_score:.2f} "
                f"| {s.pvt_score:.2f} | {s.efficiency_score:.2f} "
                f"| {s.reputation_score:.2f} | {s.total_turns} |"
            )

        lines.append(
            "\nUsa estos scores para ponderar la confianza en los argumentos de cada modelo. "
            "Un score TSA alto indica que sus argumentos tienden a sobrevivir al escrutinio. "
            "Un score PVT alto indica precisión técnica."
        )
        return "\n".join(lines)

    def invalidate_cache(self):
        """Invalida cache para forzar recarga"""
        self._loaded = False
        self._cache.clear()


# Singleton
_reputation_query_service: Optional[ReputationQueryService] = None


def get_reputation_service() -> ReputationQueryService:
    global _reputation_query_service
    if _reputation_query_service is None:
        _reputation_query_service = ReputationQueryService()
    return _reputation_query_service
