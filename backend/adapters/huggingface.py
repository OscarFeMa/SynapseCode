"""
Synapse Council v2.2 - HuggingFace Adapter
NOTA: HuggingFace depreco la Inference API gratuita.
Los modelos solo estan disponibles via:
  1. Inference Endpoints (pago): https://ui.endpoints.huggingface.co/
  2. TGI/self-hosted
  3. Proveedores alternativos: TogetherAI, Fireworks, DeepInfra

Se mantiene el adapter para compatibilidad, pero no hay endpoints
gratuitos funcionales actualmente.
"""

from typing import Any, AsyncGenerator, Dict, Optional

import structlog

from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class HuggingFaceClient:
    """Cliente informativo - HuggingFace free Inference API no disponible"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.HF_TOKEN

    def list_free_models(self) -> Dict[str, str]:
        return {}

    async def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "status": "unconfigured",
                "error": "Token no configurado",
                "note": "HuggingFace depreco la Inference API gratuita",
            }
        try:
            import httpx

            r = httpx.get(
                "https://huggingface.co/api/whoami-v2",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            user = r.json().get("name", "?") if r.status_code == 200 else "invalido"
            return {
                "status": "unavailable",
                "user": user,
                "note": "Inference API gratuita deprecada por HuggingFace. Usar Inference Endpoints (pago) o proveedores alternativos (TogetherAI, Fireworks, DeepInfra).",
            }
        except Exception as e:
            return {"status": "unavailable", "error": str(e)[:80]}

    async def chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> AsyncGenerator[str, None]:
        yield "[HuggingFace: Inference API gratuita no disponible. Alternativas: TogetherAI, Fireworks, Deepinfra (via OpenRouter)]"
