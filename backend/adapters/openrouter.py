"""
Synapse Council v2.0 - OpenRouter Adapter
Cliente async para OpenRouter API
Herencia de BaseOpenAICompatibleClient para eliminar duplicacion SSE.
Integra Circuit Breaker para evitar fallos en cascada.
"""

from collections.abc import AsyncGenerator
from typing import Any

import httpx

from backend.adapters.base import BaseOpenAICompatibleClient
from backend.adapters.circuit_breaker import circuit_breakers
from backend.config import get_settings


class OpenRouterClient(BaseOpenAICompatibleClient):
    """Cliente async para OpenRouter con Circuit Breaker"""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, settings=None):
        if settings is None:
            settings = get_settings()
        super().__init__(
            base_url=base_url or settings.OPENROUTER_BASE_URL,
            timeout=settings.OPENROUTER_TIMEOUT_SECONDS,
            max_retries=settings.OPENROUTER_MAX_RETRIES,
            api_key=api_key or settings.OPENROUTER_API_KEY,
            extra_headers={
                "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
                "X-Title": settings.OPENROUTER_APP_NAME,
            },
        )
        self.circuit_breaker = circuit_breakers.get(
            "openrouter",
            failure_threshold=settings.OPENROUTER_MAX_RETRIES + 1,
            recovery_timeout=60.0,
        )

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Chat completion con Circuit Breaker"""
        if not self.circuit_breaker.can_execute():
            raise RuntimeError(
                f"OpenRouter circuit breaker is OPEN. "
                f"Retry after {self.circuit_breaker.recovery_timeout}s"
            )

        try:
            async for token in super().chat_completion(model, messages, temperature, max_tokens, stream):
                self.circuit_breaker.record_success()
                yield token
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise e

    async def health_check(self) -> dict[str, Any]:
        """Verifica conexion con OpenRouter"""
        if not self.api_key:
            return {"status": "unconfigured", "error": "API key not set"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = self._build_headers()
                response = await client.get(f"{self.base_url}/v1/auth/key", headers=headers)

                if response.status_code == 200:
                    return {"status": "online", "key_valid": True}
                elif response.status_code == 401:
                    return {"status": "error", "error": "Invalid API key"}
                else:
                    return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "offline", "error": str(e)}
