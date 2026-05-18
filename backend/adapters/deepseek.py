"""
Synapse Council v2.1 - DeepSeek Adapter
Cliente async para DeepSeek API (OpenAI-compatible)
Integra Circuit Breaker para evitar fallos en cascada.
"""

import json
from collections.abc import AsyncGenerator

import httpx
import structlog

from backend.adapters.circuit_breaker import circuit_breakers
from backend.config import get_settings

logger = structlog.get_logger()


class DeepSeekClient:
    """Cliente async para DeepSeek Cloud con Circuit Breaker"""

    def __init__(self, api_key: str | None = None, settings=None):
        if settings is None:
            settings = get_settings()
        self._settings = settings
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = f"{settings.DEEPSEEK_BASE_URL}/chat/completions"
        self._client: httpx.AsyncClient | None = None
        self.circuit_breaker = circuit_breakers.get(
            "deepseek",
            failure_threshold=3,
            recovery_timeout=60.0,
        )

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Genera respuesta usando DeepSeek API con Circuit Breaker"""
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY no configurada")

        if not self.circuit_breaker.can_execute():
            raise RuntimeError(
                f"DeepSeek circuit breaker is OPEN. Retry after {self.circuit_breaker.recovery_timeout}s"
            )

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            if not stream:
                response = await self.client.post(self.base_url, json=payload, headers=headers)
                if response.status_code != 200:
                    err = response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
                    self.circuit_breaker.record_failure()
                    yield f"[Error DeepSeek: {err}]"
                    return
                data = response.json()
                self.circuit_breaker.record_success()
                yield data["choices"][0]["message"]["content"]
            else:
                async with self.client.stream("POST", self.base_url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        try:
                            err = json.loads(error_body).get("error", {}).get("message", f"HTTP {response.status_code}")
                        except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                            err = f"HTTP {response.status_code}: {error_body.decode()[:100]}"
                        self.circuit_breaker.record_failure()
                        yield f"[Error DeepSeek: {err}]"
                        return
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            if "[DONE]" in line:
                                break
                            try:
                                data = json.loads(line[6:])
                                delta = data["choices"][0]["delta"]
                                if "content" in delta:
                                    yield delta["content"]
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
                    self.circuit_breaker.record_success()
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error("deepseek.request_failed", error=str(e))
            yield f"[Error DeepSeek: {e!s}]"
