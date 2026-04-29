"""
Synapse Council v2.1 - Gemini Adapter
Cliente async para Google Gemini API (REST)
"""
import json
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
from backend.config import get_settings
import structlog

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

        # Gemini model names are used as-is (no suffix needed)
        # Valid models: gemini-1.5-pro, gemini-1.5-flash, gemini-1.0-pro
        gemini_model = model
        endpoint = f"{gemini_model}:streamGenerateContent" if stream else f"{gemini_model}:generateContent"
        url = f"{self.base_url}/{endpoint}?key={self.api_key}"

        try:
            async with self.client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error("gemini.api_error", status=response.status_code, error=error_body.decode())
                    yield f"[Error Gemini API: {response.status_code}]"
                    return

                async for line in response.aiter_lines():
                    if not line: continue
                    
                    # Gemini retorna un array de objetos en streaming
                    # Formato: [{"candidates": [{"content": {"parts": [{"text": "..."}]}}]}]
                    try:
                        # Eliminar posibles comas si es un stream de JSON array
                        clean_line = line.strip().lstrip("[").rstrip(",").rstrip("]")
                        if not clean_line: continue
                        
                        data = json.loads(clean_line)
                        if "candidates" in data:
                            text = data["candidates"][0]["content"]["parts"][0]["text"]
                            yield text
                    except Exception:
                        continue
        except Exception as e:
            logger.error("gemini.request_failed", error=str(e))
            yield f"[Error de conexión con Gemini: {str(e)}]"
