"""
Synapse Council v2.0 - Ollama Adapter
Cliente async para Ollama API (usa formato nativo, no OpenAI-compatible)
"""
import json
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
from backend.config import get_settings
import structlog

settings = get_settings()
logger = structlog.get_logger()


class OllamaClient:
    """Cliente async para Ollama (motor local)"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS
        self.max_retries = settings.OLLAMA_MAX_RETRIES
        self.keep_alive = settings.OLLAMA_KEEP_ALIVE
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
        
    async def health_check(self) -> Dict[str, Any]:
        """Verifica conexión con Ollama y lista modelos disponibles"""
        try:
            client = self.client
            response = await client.get(
                f"{self.base_url}/api/tags",
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "unknown") for m in data.get("models", [])]
                return {
                    "status": "online",
                    "models_available": len(models),
                    "models": models[:10],  # Primeros 10
                    "url": self.base_url
                }
            else:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "url": self.base_url
                }
        except httpx.ConnectError:
            return {
                "status": "offline",
                "error": "Cannot connect to Ollama. Is it running?",
                "url": self.base_url
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "url": self.base_url
            }
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        stream: bool = True,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Genera texto con Ollama
        Yields tokens si stream=True, o texto completo al final
        """
        logger.info("ollama.generate.start", model=model, prompt_preview=prompt[:50])
        
        # Siempre usar stream=True para asegurar consumo completo
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": options or {},
            "keep_alive": self.keep_alive,
        }
        
        if system:
            payload["system"] = system
        
        logger.info("ollama.generate.payload", payload=payload)
        
        client = self.client
        try:
            logger.info("ollama.generate.sending_request", url=f"{self.base_url}/api/generate")
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                logger.info("ollama.generate.response_started", status_code=response.status_code)
                if stream:
                    token_count = 0
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    token_count += 1
                                    yield data["response"]
                                if data.get("done", False):
                                    logger.info("ollama.generate.done", tokens_yielded=token_count)
                                    break
                            except json.JSONDecodeError:
                                continue
                    logger.info("ollama.generate.stream_completed", total_tokens=token_count)
                else:
                    text = ""
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    text += data["response"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
                    yield text
        except Exception as e:
            logger.error("ollama.generate.exception", error=str(e), error_type=type(e).__name__)
            raise e
    
    async def chat(
        self,
        model: str,
        messages: list,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Chat completion con Ollama (formato chat)
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "keep_alive": self.keep_alive,
        }
        
        client = self.client
        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise e
