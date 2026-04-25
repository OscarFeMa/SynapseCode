"""
Synapse Council v2.0 - OpenRouter Adapter
Cliente async para OpenRouter API
Hereda de BaseOpenAICompatibleClient para eliminar duplicación SSE.
"""
import httpx
from typing import Dict, Any, Optional
from backend.adapters.base import BaseOpenAICompatibleClient
from backend.config import get_settings

settings = get_settings()


class OpenRouterClient(BaseOpenAICompatibleClient):
    """Cliente async para OpenRouter"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(
            base_url=base_url or settings.OPENROUTER_BASE_URL,
            timeout=settings.OPENROUTER_TIMEOUT_SECONDS,
            max_retries=settings.OPENROUTER_MAX_RETRIES,
            api_key=api_key or settings.OPENROUTER_API_KEY,
            extra_headers={
                "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
                "X-Title": settings.OPENROUTER_APP_NAME,
            },
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica conexión con OpenRouter"""
        if not self.api_key:
            return {"status": "unconfigured", "error": "API key not set"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = self._build_headers()
                response = await client.get(f"{self.base_url}/auth/key", headers=headers)
                
                if response.status_code == 200:
                    return {"status": "online", "key_valid": True}
                elif response.status_code == 401:
                    return {"status": "error", "error": "Invalid API key"}
                else:
                    return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "offline", "error": str(e)}
