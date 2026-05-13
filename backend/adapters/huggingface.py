"""
Synapse Council v2.2 - HuggingFace Inference API Adapter
Cliente async para HuggingFace Inference API.
Modelos gratuitos: 30k requests/mes, sin tarjeta de credito.
"""
import json
import structlog
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

# Modelos gratuitos verificados en Inference API
FREE_MODELS = {
    "phi3": "microsoft/Phi-3-mini-4k-instruct",
    "llama3": "meta-llama/Meta-Llama-3-8B-Instruct",
    "gemma2": "google/gemma-2-2b-it",
    "mistral": "mistralai/Mistral-7B-Instruct-v0.3",
    "qwen2": "Qwen/Qwen2.5-7B-Instruct",
    "deepseek": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "falcon": "tiiuae/falcon-7b-instruct",
    "zephyr": "HuggingFaceH4/zephyr-7b-beta",
}


class HuggingFaceClient:
    """Cliente async para HuggingFace Inference API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.HF_TOKEN
        self.base_url = "https://api-inference.huggingface.co/models"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    @property
    def headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def list_free_models(self) -> Dict[str, str]:
        """Retorna dict de modelos gratuitos: {alias: model_id}"""
        return dict(FREE_MODELS)

    async def health_check(self) -> Dict[str, Any]:
        """Verifica conexion con HuggingFace"""
        if not self.api_key:
            return {"status": "unconfigured", "error": "HF_TOKEN no configurado", "free_models": len(FREE_MODELS)}

        # Probar con el modelo mas pequeno
        model = FREE_MODELS["phi3"]
        result = await self._inference(model, "OK", max_tokens=5)
        if "error" in result:
            return {"status": "error", "error": result["error"], "model_tested": model, "free_models": len(FREE_MODELS)}
        return {"status": "online", "model_tested": model, "free_models": len(FREE_MODELS)}

    async def chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> AsyncGenerator[str, None]:
        """
        Genera respuesta usando HuggingFace Inference API.
        El parametro `model` puede ser un alias (phi3, llama3, etc.) o un model_id completo.
        """
        if not self.api_key:
            raise ValueError("HF_TOKEN no configurado")

        model_id = FREE_MODELS.get(model, model)

        try:
            result = await self._inference(model_id, messages, temperature, max_tokens)
            if "error" in result:
                yield f"[Error HuggingFace: {result['error']}]"
                return
            yield result.get("text", "")
        except Exception as e:
            logger.error("huggingface.request_failed", error=str(e), model=model_id)
            yield f"[Error HuggingFace: {str(e)}]"

    async def _inference(
        self,
        model_id: str,
        messages_or_prompt,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """Ejecuta inferencia contra la API"""
        url = f"{self.base_url}/{model_id}"

        if isinstance(messages_or_prompt, list):
            prompt = self._messages_to_prompt(messages_or_prompt)
        else:
            prompt = messages_or_prompt if isinstance(messages_or_prompt, str) else "OK"

        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
            },
        }

        response = await self.client.post(url, json=payload, headers=self.headers)
        
        if response.status_code == 401:
            return {"error": "Token invalido. Obtener en https://huggingface.co/settings/tokens"}
        if response.status_code == 403:
            return {"error": f"Modelo {model_id} no accesible o requiere gated access"}
        if response.status_code == 503:
            return {"error": f"Modelo {model_id} cargando (puede tardar 30s)"}
        
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0:
            generated = data[0].get("generated_text", "")
            return {"text": generated}
        if isinstance(data, dict):
            if "error" in data:
                return {"error": data["error"]}
            if "generated_text" in data:
                return {"text": data["generated_text"]}
        
        return {"text": str(data)}

    def _messages_to_prompt(self, messages: list) -> str:
        """Convierte mensajes OpenAI-style a prompt plano"""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant:")
        return "\n".join(parts)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
