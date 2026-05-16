"""
Unit tests for adapters (clients)
"""
from backend.adapters.ollama import OllamaClient
from backend.adapters.groq import GroqClient
from backend.adapters.gemini import GeminiClient
from backend.adapters.lm_studio import LMStudioClient
from backend.adapters.web_agent import WebAgentClient
from backend.adapters.http_client_manager import HTTPClientManager
from backend.adapters.openrouter import OpenRouterClient


class TestAdapters:
    """Pruebas de los adaptadores de clientes"""

    def test_ollama_client(self):
        client = OllamaClient()
        assert hasattr(client, "chat")
        assert hasattr(client, "generate")
        assert hasattr(client, "health_check")
        assert hasattr(client, "warm_model")
        assert hasattr(client, "unload_model")
        assert hasattr(client, "pull_model")

    def test_groq_client(self):
        client = GroqClient()
        assert hasattr(client, "chat_completion")
        assert hasattr(client, "health_check")

    def test_gemini_client(self):
        client = GeminiClient()
        assert hasattr(client, "chat_completion")
        assert hasattr(client, "health_check")

    def test_lm_studio_client(self):
        client = LMStudioClient()
        assert hasattr(client, "chat_completion")
        assert hasattr(client, "health_check")

    def test_http_client_manager(self):
        manager = HTTPClientManager()
        assert hasattr(manager, "get_client")
        assert hasattr(manager, "close_all")

    def test_openrouter_client(self):
        client = OpenRouterClient()
        assert hasattr(client, "chat_completion")
        assert hasattr(client, "health_check")
