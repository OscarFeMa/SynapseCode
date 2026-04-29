"""
Synapse Council v2.1 - DeepSeek Adapter
Cliente async para DeepSeek API (OpenAI-compatible)
"""
import json
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
from backend.config import get_settings
import structlog

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
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Genera respuesta usando DeepSeek API"""
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY no configurada")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            if not stream:
                response = await self.client.post(self.base_url, json=payload, headers=headers)
                data = response.json()
                yield data["choices"][0]["message"]["content"]
            else:
                async with self.client.stream("POST", self.base_url, json=payload, headers=headers) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            if "[DONE]" in line: break
                            try:
                                data = json.loads(line[6:])
                                delta = data["choices"][0]["delta"]
                                if "content" in delta:
                                    yield delta["content"]
                            except:
                                continue
        except Exception as e:
            logger.error("deepseek.request_failed", error=str(e))
            yield f"[Error DeepSeek: {str(e)}]"
