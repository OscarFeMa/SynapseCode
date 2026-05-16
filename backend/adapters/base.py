"""
Synapse Council v2.0 - Base Adapter
Clase base para clientes OpenAI-compatible (LM Studio, Jan, OpenRouter)
Elimina duplicación de lógica SSE entre adaptadores.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import structlog

logger = structlog.get_logger()

# Lazy init del semantic cache
_semantic_cache = None


def _get_semantic_cache():
    global _semantic_cache
    if _semantic_cache is None:
        from backend.caching.semantic_cache import semantic_cache

        _semantic_cache = semantic_cache
    return _semantic_cache


class BaseOpenAICompatibleClient(ABC):
    """
    Cliente base para APIs compatibles con el formato OpenAI.
    Encapsula el parsing de Server-Sent Events (SSE).
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 120,
        max_retries: int = 2,
        api_key: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_key = api_key
        self.extra_headers = extra_headers or {}
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Cliente HTTPX persistente (Connection Pooling)"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """Cierra el cliente persistente explícitamente"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verifica conexión con el servicio"""
        ...

    def _build_headers(self) -> Dict[str, str]:
        """Construye headers para la petición"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        return headers

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Chat completion con formato OpenAI y caché semántica.
        Parsing SSE unificado para todos los adaptadores compatibles.
        """
        # Convertir messages a prompt string para caché
        prompt = json.dumps(messages)

        # Buscar en caché semántica (solo si no es streaming)
        if not stream:
            cache = _get_semantic_cache()
            cached = await cache.get(
                prompt=prompt,
                model=model,
                engine=self.base_url.split("://")[1].split(":")[0]
                if "://" in self.base_url
                else "local",
                node="LOCAL"
                if "localhost" in self.base_url or "127.0.0.1" in self.base_url
                else "CLOUD",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if cached:
                logger.info(
                    "openai_base.cache_hit",
                    model=model,
                    similarity=cached.get("similarity"),
                )
                yield cached["response_text"]
                return

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = self._build_headers()
        client = self.client

        retry_delay = 2.0
        start_time = time.time()
        response_text = ""

        for attempt in range(self.max_retries + 1):
            try:
                if stream:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/v1/chat/completions",
                        json=payload,
                        headers=headers,
                    ) as response:
                        if response.status_code == 429:
                            if attempt < self.max_retries:
                                logger.warning(
                                    "openai_base.rate_limit_stream",
                                    attempt=attempt + 1,
                                    wait=retry_delay,
                                    url=self.base_url,
                                )
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2
                                continue

                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:]  # Remover "data: "
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content")
                                    if content:
                                        response_text += content
                                        yield content
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
                        return
                else:
                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                    if response.status_code == 429:
                        if attempt < self.max_retries:
                            logger.warning(
                                "openai_base.rate_limit",
                                attempt=attempt + 1,
                                wait=retry_delay,
                                url=self.base_url,
                            )
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue

                    response.raise_for_status()
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        text = choices[0].get("message", {}).get("content", "")
                        response_text = text

                        # Guardar en caché
                        latency_ms = int((time.time() - start_time) * 1000)
                        cache = _get_semantic_cache()
                        await cache.set(
                            prompt=prompt,
                            response_text=response_text,
                            model=model,
                            engine=self.base_url.split("://")[1].split(":")[0]
                            if "://" in self.base_url
                            else "local",
                            node="LOCAL"
                            if "localhost" in self.base_url
                            or "127.0.0.1" in self.base_url
                            else "CLOUD",
                            temperature=temperature,
                            max_tokens=max_tokens,
                            tokens_in=len(prompt),
                            tokens_out=len(response_text),
                            latency_ms=latency_ms,
                        )

                        yield text
                    return
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(
                        "openai_base.request_failed_final",
                        error=str(e),
                        url=self.base_url,
                    )
                    raise e
                else:
                    logger.warning(
                        "openai_base.request_failed_retry",
                        attempt=attempt + 1,
                        error=str(e),
                        url=self.base_url,
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2

    async def completion(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Text completion simple (convierte a chat format)"""
        messages = [{"role": "user", "content": prompt}]
        result = ""
        async for token in self.chat_completion(
            model, messages, temperature, max_tokens, stream=False
        ):
            result += token
        return result

    async def _check_models_endpoint(self) -> Dict[str, Any]:
        """Helper para verificar /v1/models (compartido entre servicios)"""
        try:
            # Usar un timeout corto específico para health check sin usar el persistente
            # O usar el persistente con un override de timeout, pero httpx.AsyncClient permite
            # override de timeout en la petición
            client = self.client
            headers = self._build_headers()
            response = await client.get(
                f"{self.base_url}/v1/models", headers=headers, timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                models = [m.get("id", "unknown") for m in data.get("data", [])]
                return {
                    "status": "online",
                    "models_available": len(models),
                    "models": models,
                    "url": self.base_url,
                }
            else:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "url": self.base_url,
                }
        except httpx.ConnectError:
            return {
                "status": "offline",
                "error": f"Cannot connect to {self.base_url}. Is it running?",
                "url": self.base_url,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "url": self.base_url}
