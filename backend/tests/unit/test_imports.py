"""
Unit tests for imports and module structure
"""
from backend.config import get_settings
from backend.database.models import SequentialDebate, SequentialDebateTurn
from backend.engine.debate_models import AgentRole, DebateAgent, DebateTurn, DebateSession
from backend.adapters.ollama import OllamaClient
from backend.adapters.groq import GroqClient
from backend.adapters.gemini import GeminiClient
from backend.adapters.lm_studio import LMStudioClient
from backend.adapters.web_agent import WebAgentClient
from backend.adapters.http_client_manager import HTTPClientManager
from backend.engine.sequential_debate_controller import SequentialDebateController
from backend.engine.tribunal import TribunalCouncil
from backend.engine.convergence import ConvergenceEvaluator
from backend.engine.quality_monitor import QualityMonitor
from backend.engine.reputation_unified import ReputationManager
from backend.engine.task_manager import TaskConfig
from backend.engine.worker_launcher import WorkerServiceManager
from backend.api.routes.health import router as health_router
from backend.api.routes.system import router as system_router
from backend.api.routes.debate import router as debate_router
from backend.main import app
from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2


class TestImports:
    """Verifica que todos los modulos se importan correctamente"""

    def test_config(self):
        s = get_settings()
        assert s.NODE_ROLE in ("MASTER", "WORKER")
        assert s.PORT == 8000

    def test_database_models(self):
        assert hasattr(SequentialDebate, "id")
        assert hasattr(SequentialDebateTurn, "debate_id")

    def test_debate_models(self):
        assert AgentRole.ANALYST.value == "analyst"
        assert hasattr(DebateSession, "tribunal_verdict")
        assert hasattr(DebateSession, "structured_report")

    def test_adapters(self):
        assert OllamaClient
        assert GroqClient
        assert GeminiClient

    def test_engine(self):
        assert SequentialDebateController
        assert TribunalCouncil
        assert ConvergenceEvaluator

    def test_routes(self):
        assert len(health_router.routes) >= 3
        assert len(system_router.routes) >= 5

    def test_main_app(self):
        assert app.title == "Synapse Council v2.0"
        assert len(app.routes) > 10

    def test_hybrid_memory(self):
        mem = get_hybrid_memory_v2()
        assert mem is not None

    def test_tribunal_config_module(self):
        from backend.engine.tribunal_config import build_tribunal_config
        config = build_tribunal_config(get_settings())
        assert set(config.keys()) == {"evidence", "risk", "alignment"}
        assert config["evidence"].primary.slot == "magistrate_evidence"
        assert config["risk"].primary.slot == "magistrate_risk"
        assert config["alignment"].primary.node == "LOCAL"
        assert all(role_config.chain for role_config in config.values())
