"""
Synapse Council v2.1 - Groq Adapter
Cliente async para Groq Cloud API (OpenAI-compatible)
"""

import json
import time
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

# Lazy init del semantic cache
_semantic_cache = None


def _get_semantic_cache():
    global _semantic_cache
    if _semantic_cache is None:
        from backend.caching.semantic_cache import semantic_cache

        _semantic_cache = semantic_cache
    return _semantic_cache


class GroqClient:
    """Cliente async para Groq Cloud (Inferencia Ultra-rápida)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    @retry(
        wait=wait_exponential(multiplier=2, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Genera respuesta usando Groq API con caché semántica"""
        if not self.api_key:
            raise ValueError("GROQ_API_KEY no configurada")

        # Convertir messages a prompt string para caché
        prompt = json.dumps(messages)

        # Buscar en caché semántica (solo si no es streaming)
        if not stream:
            cache = _get_semantic_cache()
            cached = await cache.get(
                prompt=prompt,
                model=model,
                engine="groq",
                node="CLOUD",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if cached:
                logger.info(
                    "groq.cache_hit", model=model, similarity=cached.get("similarity")
                )
                yield cached["response_text"]
                return

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

        start_time = time.time()
        response_text = ""

        try:
            if not stream:
                response = await self.client.post(
                    self.base_url, json=payload, headers=headers
                )
                if response.status_code == 429:
                    logger.warning("groq.rate_limit_retry")
                    raise httpx.HTTPStatusError(
                        "Rate Limit", request=response.request, response=response
                    )

                response.raise_for_status()
                data = response.json()
                response_text = data["choices"][0]["message"]["content"]
                latency_ms = int((time.time() - start_time) * 1000)

                # Guardar en caché
                cache = _get_semantic_cache()
                await cache.set(
                    prompt=prompt,
                    response_text=response_text,
                    model=model,
                    engine="groq",
                    node="CLOUD",
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tokens_in=len(prompt),
                    tokens_out=len(response_text),
                    latency_ms=latency_ms,
                )

                yield response_text
                return
            else:
                async with self.client.stream(
                    "POST", self.base_url, json=payload, headers=headers
                ) as response:
                    if response.status_code == 429:
                        logger.warning("groq.rate_limit_retry_stream")
                        raise httpx.HTTPStatusError(
                            "Rate Limit", request=response.request, response=response
                        )

                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            if "[DONE]" in line:
                                break
                            try:
                                data = json.loads(line[6:])
                                delta = data["choices"][0]["delta"]
                                if "content" in delta:
                                    response_text += delta["content"]
                                    yield delta["content"]
                            except:
                                continue
                    return
        except httpx.HTTPStatusError:
            raise
        except Exception as e:
            logger.error("groq.request_failed", error=str(e))
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Verifica si la API key es valida listando modelos"""
        if not self.api_key:
            return {"status": "unconfigured", "error": "GROQ_API_KEY no configurada"}
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://api.groq.com/openai/v1/models", headers=headers
                )
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "status": "online",
                        "models_available": len(data.get("data", [])),
                    }
                elif r.status_code == 401:
                    return {"status": "error", "error": "API key invalida"}
                else:
                    return {"status": "error", "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:80]}
