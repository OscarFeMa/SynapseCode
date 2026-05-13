"""
Synapse Council v2.1 - Gemini Adapter
Cliente async para Google Gemini API (REST)
"""
import asyncio
import json
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
from backend.config import get_settings
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

settings = get_settings()
logger = structlog.get_logger()

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
        """Genera respuesta usando Gemini API"""
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
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction

        gemini_model = model
        endpoint = f"{gemini_model}:streamGenerateContent" if stream else f"{gemini_model}:generateContent"
        url = f"{self.base_url}/{endpoint}?key={self.api_key}"

        max_retries = 3
        retry_delay = 2.0

        try:
            async with self.client.stream("POST", url, json=payload) as response:
                if response.status_code == 429:
                    logger.warning("gemini.rate_limit_retry")
                    raise httpx.HTTPStatusError("Rate Limit", request=response.request, response=response)
                
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error("gemini.api_error", status=response.status_code, error=error_body.decode())
                    yield f"[Error Gemini API: {response.status_code}]"
                    return

                buffer = ""
                async for line in response.aiter_lines():
                    if not line: continue
                    buffer += line.strip()
                    
                    # Intentar parsear JSON cuando tengamos un objeto completo
                    try:
                        # Gemini devuelve un array: [{...}, {...}]
                        # o un solo objeto: {...}
                        clean = buffer.lstrip("[").rstrip(",").rstrip("]")
                        if not clean: continue
                        
                        data = json.loads(clean)
                        if "candidates" in data:
                            parts = data["candidates"][0]["content"]["parts"]
                            for part in parts:
                                if "text" in part:
                                    yield part["text"]
                        buffer = ""
                    except json.JSONDecodeError:
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
                    models = [m["name"].split("/")[-1] for m in data.get("models", [])
                             if "generateContent" in m.get("supportedGenerationMethods", [])]
                    return {"status": "online", "models_available": len(models), "models": models[:5]}
                elif r.status_code == 403:
                    return {"status": "error", "error": "API key sin permisos. Habilitar billing en Google Cloud"}
                else:
                    return {"status": "error", "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:80]}
