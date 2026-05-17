"""
Synapse Council v2.1 - DeepSeek Adapter
Cliente async para DeepSeek API (OpenAI-compatible)
"""

import json
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
import structlog

from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class DeepSeekClient:
    """Cliente async para DeepSeek Cloud"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = f"{settings.DEEPSEEK_BASE_URL}/chat/completions"
        self._client: Optional[httpx.AsyncClient] = None

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
        """Genera respuesta usando DeepSeek API"""
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY no configurada")

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
                    yield f"[Error DeepSeek: {err}]"
                    return
                data = response.json()
                yield data["choices"][0]["message"]["content"]
            else:
                async with self.client.stream("POST", self.base_url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        try:
                            err = json.loads(error_body).get("error", {}).get("message", f"HTTP {response.status_code}")
                        except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                            err = f"HTTP {response.status_code}: {error_body.decode()[:100]}"
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
        except Exception as e:
            logger.error("deepseek.request_failed", error=str(e))
            yield f"[Error DeepSeek: {str(e)}]"

    async def health_check(self) -> Dict[str, Any]:
        """Verifica si la API key es valida listando modelos"""
        if not self.api_key:
            return {"status": "unconfigured", "error": "DEEPSEEK_API_KEY no configurada"}
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{settings.DEEPSEEK_BASE_URL}/models", headers=headers)
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
