"""
Synapse Council - Tests de integracion y importacion
Ejecutar: pytest backend/tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestImports:
    """Verifica que todos los modulos se importan correctamente"""

    def test_config(self):
        from backend.config import get_settings
        s = get_settings()
        assert s.NODE_ROLE in ("MASTER", "WORKER")
        assert s.PORT == 8000

    def test_database_models(self):
        from backend.database.models import SequentialDebate, SequentialDebateTurn
        assert hasattr(SequentialDebate, "id")
        assert hasattr(SequentialDebateTurn, "debate_id")

    def test_debate_models(self):
        from backend.engine.debate_models import AgentRole, DebateAgent, DebateTurn, DebateSession
        assert AgentRole.ANALYST.value == "analyst"
        assert hasattr(DebateSession, "tribunal_verdict")
        assert hasattr(DebateSession, "structured_report")

    def test_adapters(self):
        from backend.adapters.ollama import OllamaClient
        from backend.adapters.groq import GroqClient
        from backend.adapters.gemini import GeminiClient
        from backend.adapters.lm_studio import LMStudioClient
        from backend.adapters.web_agent import WebAgentClient
        from backend.adapters.http_client_manager import HTTPClientManager
        assert OllamaClient
        assert GroqClient
        assert GeminiClient

    def test_engine(self):
        from backend.engine.sequential_debate_controller import SequentialDebateController
        from backend.engine.tribunal import TribunalCouncil
        from backend.engine.convergence import ConvergenceEvaluator
        from backend.engine.quality_monitor import QualityMonitor
        from backend.engine.reputation_unified import ReputationManager
        from backend.engine.task_manager import TaskConfig
        from backend.engine.worker_launcher import WorkerServiceManager
        assert SequentialDebateController
        assert TribunalCouncil
        assert ConvergenceEvaluator

    def test_routes(self):
        from backend.api.routes.health import router as health_router
        from backend.api.routes.system import router as system_router
        from backend.api.routes.debate import router as debate_router
        assert len(health_router.routes) >= 3
        assert len(system_router.routes) >= 5

    def test_main_app(self):
        from backend.main import app
        assert app.title == "Synapse Council v3.0"
        assert len(app.routes) > 10

    def test_hybrid_memory(self):
        from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2
        mem = get_hybrid_memory_v2()
        assert mem is not None


class TestConfig:
    """Verifica configuraciones basicas"""

    def test_env_vars(self):
        from backend.config import get_settings
        s = get_settings()
        # Verificar que URL de servicios no tengan placeholders
        assert "CHANGEME" not in (s.SUPABASE_URL or ""), "SUPABASE_URL contiene CHANGEME"
        assert "CHANGEME" not in (s.SUPABASE_ANON_KEY or ""), "SUPABASE_ANON_KEY contiene CHANGEME"

    def test_worker_urls(self):
        from backend.config import get_settings
        s = get_settings()
        if s.is_master:
            host = s.get_worker_host()
            assert host is not None, "Worker host no resuelto"
            assert s.worker_ollama_url.startswith("http://")
            assert s.worker_lm_studio_url.startswith("http://")


class TestAPIEndpoints:
    """Pruebas de endpoints via requests mock"""

    def test_health_response_shape(self):
        """Verifica que el health check tenga la estructura correcta"""
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data
        assert "database" in data["services"]

    def test_health_live(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        r = client.get("/health/live")
        assert r.status_code == 200
        assert r.json()["status"] == "alive"

    def test_debate_list_shape(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        r = client.get("/api/v1/debates/list")
        assert r.status_code == 200
        data = r.json()
        assert "count" in data
        assert "sessions" in data

    def test_create_debate_invalid(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        r = client.post("/api/v1/debates/create", json={})
        # Debe fallar por falta de topic
        assert r.status_code in (400, 422)
