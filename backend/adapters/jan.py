"""
Synapse Council v2.0 - Jan.ai Adapter
Cliente async para Jan API (compatible OpenAI)
Hereda de BaseOpenAICompatibleClient para eliminar duplicación SSE.
"""

from typing import Any, Dict, Optional

from backend.adapters.base import BaseOpenAICompatibleClient
from backend.config import get_settings

settings = get_settings()


class JanClient(BaseOpenAICompatibleClient):
    """Cliente async para Jan.ai (API compatible en puerto 1337)"""

    def __init__(self, base_url: Optional[str] = None):
        super().__init__(
            base_url=base_url or settings.JAN_BASE_URL,
            timeout=settings.JAN_TIMEOUT_SECONDS,
            max_retries=settings.JAN_MAX_RETRIES,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Verifica conexión con Jan.ai"""
        return await self._check_models_endpoint()
