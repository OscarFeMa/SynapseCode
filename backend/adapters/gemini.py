"""
Synapse Council v2.1 - Gemini Adapter
Cliente async para Google Gemini API (REST)
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


class GeminiClient:
    """Cliente async para Google Gemini (AI Studio)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=90.0)
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
        """Genera respuesta usando Gemini API con caché semántica"""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY no configurada")

        # Convertir mensajes de formato OpenAI a Gemini
        contents = []
        system_instruction = None

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = {"parts": [{"text": msg["content"]}]}
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Convertir messages a prompt string para caché
        prompt = json.dumps(messages)

        # Buscar en caché semántica (solo si no es streaming)
        if not stream:
            cache = _get_semantic_cache()
            cached = await cache.get(
                prompt=prompt,
                model=model,
                engine="gemini",
                node="CLOUD",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if cached:
                logger.info(
                    "gemini.cache_hit", model=model, similarity=cached.get("similarity")
                )
                yield cached["response_text"]
                return

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction

        gemini_model = model
        endpoint = (
            f"{gemini_model}:streamGenerateContent"
            if stream
            else f"{gemini_model}:generateContent"
        )
        url = f"{self.base_url}/{endpoint}?key={self.api_key}"

        start_time = time.time()
        response_text = ""

        try:
            async with self.client.stream("POST", url, json=payload) as response:
                if response.status_code == 429:
                    logger.warning("gemini.rate_limit_retry")
                    raise httpx.HTTPStatusError(
                        "Rate Limit", request=response.request, response=response
                    )

                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(
                        "gemini.api_error",
                        status=response.status_code,
                        error=error_body.decode(),
                    )
                    yield f"[Error Gemini API: {response.status_code}]"
                    return

                buffer = ""
                if not stream:
                    # Modo no-streaming: acumular toda la respuesta
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        buffer += line.strip()

                        try:
                            clean = buffer.lstrip("[").rstrip(",").rstrip("]")
                            if not clean:
                                continue

                            data = json.loads(clean)
                            if "candidates" in data:
                                parts = data["candidates"][0]["content"]["parts"]
                                for part in parts:
                                    if "text" in part:
                                        response_text += part["text"]
                            buffer = ""
                        except json.JSONDecodeError:
                            continue

                    # Guardar en caché
                    latency_ms = int((time.time() - start_time) * 1000)
                    cache = _get_semantic_cache()
                    await cache.set(
                        prompt=prompt,
                        response_text=response_text,
                        model=model,
                        engine="gemini",
                        node="CLOUD",
                        temperature=temperature,
                        max_tokens=max_tokens,
                        tokens_in=len(prompt),
                        tokens_out=len(response_text),
                        latency_ms=latency_ms,
                    )

                    yield response_text
                else:
                    # Modo streaming
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        buffer += line.strip()

                        try:
                            clean = buffer.lstrip("[").rstrip(",").rstrip("]")
                            if not clean:
                                continue

                            data = json.loads(clean)
                            if "candidates" in data:
                                parts = data["candidates"][0]["content"]["parts"]
                                for part in parts:
                                    if "text" in part:
                                        response_text += part["text"]
                                        yield part["text"]
                            buffer = ""
                        except json.JSONDecodeError:
                            continue
                        continue  # Acumular más líneas
        except httpx.HTTPStatusError:
            raise
        except Exception as e:
            logger.error("gemini.request_failed", error=str(e))
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Verifica si la API key es valida listando modelos disponibles"""
        if not self.api_key:
            return {"status": "unconfigured", "error": "GEMINI_API_KEY no configurada"}
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    models = [
                        m["name"].split("/")[-1]
                        for m in data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    return {
                        "status": "online",
                        "models_available": len(models),
                        "models": models[:5],
                    }
                elif r.status_code == 403:
                    return {
                        "status": "error",
                        "error": "API key sin permisos. Habilitar billing en Google Cloud",
                    }
                else:
                    return {"status": "error", "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:80]}
