"""
Synapse Council v2.0 - Model Adapters
Clientes async para conectar con diferentes motores de IA
"""

from backend.adapters.base import BaseOpenAICompatibleClient
from backend.adapters.jan import JanClient
from backend.adapters.lm_studio import LMStudioClient
from backend.adapters.ollama import OllamaClient
from backend.adapters.openrouter import OpenRouterClient
from backend.adapters.web_agent import WebAgentClient

__all__ = [
    "BaseOpenAICompatibleClient",
    "JanClient",
    "LMStudioClient",
    "OllamaClient",
    "OpenRouterClient",
    "WebAgentClient",
]
