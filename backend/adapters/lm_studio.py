"""
Synapse Council v2.0 - LM Studio Adapter
Cliente async para LM Studio API (compatible OpenAI)
Hereda de BaseOpenAICompatibleClient para eliminar duplicación SSE.
"""

from typing import Any

from backend.adapters.base import BaseOpenAICompatibleClient
from backend.config import get_settings

settings = get_settings()


class LMStudioClient(BaseOpenAICompatibleClient):
    """Cliente async para LM Studio (API OpenAI-compatible en puerto 1234/1235)"""

    def __init__(self, base_url: str | None = None):
        super().__init__(
            base_url=base_url or settings.LM_STUDIO_BASE_URL,
            timeout=settings.LM_STUDIO_TIMEOUT_SECONDS,
            max_retries=settings.LM_STUDIO_MAX_RETRIES,
        )

    async def health_check(self) -> dict[str, Any]:
        """Verifica conexión con LM Studio"""
        return await self._check_models_endpoint()
