"""
Synapse Council v2.1 - Groq Adapter
Cliente async para Groq Cloud API (OpenAI-compatible)
"""
import json
import httpx
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from backend.config import get_settings
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

settings = get_settings()
logger = structlog.get_logger()

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
        reraise=True
    )
    async def chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Genera respuesta usando Groq API"""
        if not self.api_key:
            raise ValueError("GROQ_API_KEY no configurada")

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

        max_retries = 3
        retry_delay = 2.0

        try:
            if not stream:
                response = await self.client.post(self.base_url, json=payload, headers=headers)
                if response.status_code == 429:
                    logger.warning("groq.rate_limit_retry")
                    raise httpx.HTTPStatusError("Rate Limit", request=response.request, response=response)
                
                response.raise_for_status()
                data = response.json()
                yield data["choices"][0]["message"]["content"]
                return
            else:
                async with self.client.stream("POST", self.base_url, json=payload, headers=headers) as response:
                    if response.status_code == 429:
                        logger.warning("groq.rate_limit_retry_stream")
                        raise httpx.HTTPStatusError("Rate Limit", request=response.request, response=response)
                    
                    response.raise_for_status()
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
                    return
        except httpx.HTTPStatusError:
            raise
        except Exception as e:
            logger.error("groq.request_failed", error=str(e))
            raise
