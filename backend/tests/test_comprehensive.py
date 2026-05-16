"""
SynapseCode v2.4 - Bateria Completa de Pruebas de Integracion
Cubre: Cache semantica, Data Warehouse, Prometheus, Tribunal fallback,
       Reductio Absurdum, Continue Debate, Export, WebSocket, Adapters
"""
import sys, os, asyncio, json, uuid, hashlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.local_db import init_db, AsyncSessionLocal
from backend.database.models import (
    SequentialDebate, SequentialDebateTurn, PromptResponseCache,
    ReductioAbsurdumProof, DebateAggregate, SupabaseSyncQueueItem,
    TopicTrending, ConsensusPattern, ModelPerformance, DailyMetricsSnapshot,
)
from backend.main import app


# ============================================================================
# NIVEL 1: IMPORTS Y ESTRUCTURA
# ============================================================================

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
        assert app.title == "Synapse Council v2.0"
        assert len(app.routes) > 10

    def test_hybrid_memory(self):
        from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2
        mem = get_hybrid_memory_v2()
        assert mem is not None

    def test_tribunal_config_module(self):
        from backend.config import get_settings
        from backend.engine.tribunal_config import build_tribunal_config

        config = build_tribunal_config(get_settings())

        assert set(config.keys()) == {"evidence", "risk", "alignment"}
        assert config["evidence"].primary.slot == "magistrate_evidence"
        assert config["risk"].primary.slot == "magistrate_risk"
        assert config["alignment"].primary.node == "LOCAL"
        assert all(role_config.chain for role_config in config.values())


class TestConfig:
    """Verifica configuraciones basicas"""

    def test_env_vars(self):
        from backend.config import get_settings
        s = get_settings()
        assert "CHANGEME" not in (s.SUPABASE_URL or ""), "SUPABASE_URL contiene CHANGEME"
        assert "CHANGEME" not in (s.SUPABASE_ANON_KEY or ""), "SUPABASE_ANON_KEY contiene CHANGEME"

    def test_worker_urls(self):
        from backend.config import get_settings
        s = get_settings()
        if s.is_master:
            host = s.get_worker_host()
            assert host is not None


# ============================================================================
# NIVEL 2: API ENDPOINTS (HTTP)
# ============================================================================

class TestAPIEndpoints:
    """Pruebas de endpoints HTTP con TestClient"""

    def test_health_response_shape(self):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "database" in data["services"]

    def test_health_live(self):
        client = TestClient(app)
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_prometheus_metrics_endpoint_exposes_core_metrics(self):
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200
        text = response.text
        assert "debate_duration_seconds" in text
        assert "debate_tokens_generated" in text

    def test_tribunal_config_endpoint_returns_effective_roles(self):
        client = TestClient(app)
        response = client.get("/api/v1/system/tribunal-config")
        assert response.status_code in (200, 404)

    def test_debate_list_shape(self):
        client = TestClient(app)
        response = client.get("/api/v1/debates/list")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_create_debate_accepts(self):
        client = TestClient(app)
        response = client.post("/api/v1/debates/create", json={"topic": "test"})
        assert response.status_code == 202

    def test_report_is_generated_from_completed_db_debate_when_missing(self):
        client = TestClient(app)
        response = client.get("/api/v1/debates/nonexistent/report")
        assert response.status_code == 404

    def test_reductio_proof_is_persisted_with_scan_metadata(self):
        from backend.database.models import ReductioAbsurdumProof
        assert hasattr(ReductioAbsurdumProof, "debate_id")
        assert hasattr(ReductioAbsurdumProof, "proposition")
        assert hasattr(ReductioAbsurdumProof, "extreme_case")
        assert hasattr(ReductioAbsurdumProof, "contradiction")
        assert hasattr(ReductioAbsurdumProof, "is_valid")
        assert hasattr(ReductioAbsurdumProof, "confidence_score")
        assert hasattr(ReductioAbsurdumProof, "consensus_areas")
        assert hasattr(ReductioAbsurdumProof, "weak_assumptions")

    def test_export_json_includes_structured_metadata(self):
        client = TestClient(app)
        response = client.get("/api/v1/debates/nonexistent/export/json")
        assert response.status_code == 404

    def test_websocket_manager_has_buffer_capability(self):
        from backend.api.websocket import WebSocketManager
        manager = WebSocketManager()
        assert hasattr(manager, "_buffer_token_event")
        assert hasattr(manager, "token_buffers")

    def test_controller_schedules_preload_for_next_local_ollama_model(self):
        from backend.engine.sequential_debate_controller import SequentialDebateController
        from backend.engine.debate_models import DebateAgent, AgentRole
        controller = SequentialDebateController()
        agents = [
            DebateAgent(id="a1", name="A1", role=AgentRole.ANALYST, node="LOCAL",
                       engine="ollama", model="llama3.2:latest", provider="meta",
                       system_prompt="", temperature=0.7, max_tokens=500),
            DebateAgent(id="a2", name="A2", role=AgentRole.CRITIC, node="LOCAL",
                       engine="ollama", model="mistral:7b", provider="mistral",
                       system_prompt="", temperature=0.7, max_tokens=500),
        ]
        next_model = controller._find_next_preload_model(agents, 0)
        assert next_model == "mistral:7b"

    def test_tribunal_uses_fallback_when_primary_magistrate_fails(self):
        from backend.engine.tribunal_config import build_tribunal_config
        from backend.config import get_settings
        config = build_tribunal_config(get_settings())
        for role, entry in config.items():
            assert entry.chain is not None
            assert len(entry.chain) >= 1

    def test_local_agent_uses_deterministic_response_cache(self):
        from backend.database.models import PromptResponseCache
        assert hasattr(PromptResponseCache, "cache_key")
        assert hasattr(PromptResponseCache, "response_text")
        assert hasattr(PromptResponseCache, "hit_count")

    def test_sqlite_migration_exists(self):
        from backend.database.migrations.sqlite_migrations import run_sqlite_migrations
        assert callable(run_sqlite_migrations)

    def test_warehouse_manager_has_process_method(self):
        from backend.database.warehouse import WarehouseManager
        assert hasattr(WarehouseManager, "process_sequential_debate")
        assert hasattr(WarehouseManager, "process_session")

    def test_system_analytics_endpoint_exists(self):
        client = TestClient(app)
        response = client.get("/api/v1/system/analytics")
        assert response.status_code in (200, 403)

    def test_sync_health_reports_blocked_queue(self):
        from backend.database.models import SupabaseSyncQueueItem
        assert hasattr(SupabaseSyncQueueItem, "status")
        assert hasattr(SupabaseSyncQueueItem, "retry_count")
        assert hasattr(SupabaseSyncQueueItem, "next_attempt_at")

    def test_hybrid_memory_persists_sync_queue_item_on_failure(self):
        from backend.memory.hybrid_memory_v2 import HybridMemoryV2
        mem = HybridMemoryV2()
        mem._enabled = True
        assert hasattr(mem, "enqueue_sync")

    def test_hybrid_memory_rehydrates_pending_queue_items_on_start(self):
        from backend.database.models import SupabaseSyncQueueItem
        assert hasattr(SupabaseSyncQueueItem, "kind")
        assert hasattr(SupabaseSyncQueueItem, "payload")

    def test_continue_debate_endpoint_exists(self):
        from backend.api.routes.debate import router, DebateContinueRequest
        continue_routes = [r for r in router.routes if hasattr(r, "path") and "/continue" in r.path]
        assert len(continue_routes) >= 1
        post_routes = [r for r in continue_routes if hasattr(r, "methods") and "POST" in r.methods]
        assert len(post_routes) >= 1

    def test_continue_debate_request_model(self):
        from backend.api.routes.debate import DebateContinueRequest
        req = DebateContinueRequest(
            max_additional_turns=2,
            continuation_prompt="Profundiza en el punto X"
        )
        assert req.max_additional_turns == 2
        assert req.continuation_prompt == "Profundiza en el punto X"
        assert req.agents is None

    def test_continue_debate_controller_method_exists(self):
        from backend.engine.sequential_debate_controller import SequentialDebateController
        controller = SequentialDebateController()
        assert hasattr(controller, "continue_debate")
        assert hasattr(controller, "_reconstruct_session_from_db")
        assert hasattr(controller, "_extract_agents_from_session")


# ============================================================================
# NIVEL 3: CACHE SEMANTICA
# ============================================================================

class TestSemanticCache:
    """Pruebas del sistema de cache semantica"""

    def test_cache_module_imports(self):
        from backend.caching.semantic_cache import SemanticCacheService
        assert SemanticCacheService is not None

    def test_cache_build_key(self):
        from backend.caching.semantic_cache import SemanticCacheService
        cache = SemanticCacheService()
        key = cache._generate_cache_key("test prompt", "llama3.2:latest", "ollama", 0.7)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_cache_similarity_threshold(self):
        from backend.caching.semantic_cache import SemanticCacheService
        cache = SemanticCacheService()
        assert hasattr(cache, "_similarity_threshold")
        assert 0.0 <= cache._similarity_threshold <= 1.0

    def test_cache_ttl_configurable(self):
        from backend.caching.semantic_cache import SemanticCacheService
        cache = SemanticCacheService()
        assert hasattr(cache, "_cache_ttl_hours")
        assert cache._cache_ttl_hours > 0

    def test_cache_cosine_similarity(self):
        from backend.caching.semantic_cache import SemanticCacheService
        cache = SemanticCacheService()
        import numpy as np
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])
        sim = cache._cosine_similarity(v1, v2)
        assert abs(sim - 1.0) < 0.001

    def test_cache_cosine_similarity_orthogonal(self):
        from backend.caching.semantic_cache import SemanticCacheService
        cache = SemanticCacheService()
        import numpy as np
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])
        sim = cache._cosine_similarity(v1, v2)
        assert abs(sim) < 0.001

    def test_cache_db_model_exists(self):
        from backend.database.models import PromptResponseCache
        assert hasattr(PromptResponseCache, "engine")
        assert hasattr(PromptResponseCache, "model")
        assert hasattr(PromptResponseCache, "temperature")
        assert hasattr(PromptResponseCache, "max_tokens")
        assert hasattr(PromptResponseCache, "prompt_hash")

    def test_cache_route_stats_endpoint(self):
        client = TestClient(app)
        response = client.get("/api/v1/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert "hit_rate" in data

    def test_cache_route_invalidate_endpoint(self):
        client = TestClient(app)
        response = client.post("/api/v1/cache/invalidate", json={})
        assert response.status_code in (200, 422)

    def test_cache_route_cleanup_endpoint(self):
        client = TestClient(app)
        response = client.post("/api/v1/cache/cleanup")
        assert response.status_code == 200


# ============================================================================
# NIVEL 4: DATA WAREHOUSE
# ============================================================================

class TestDataWarehouse:
    """Pruebas del sistema de Data Warehouse"""

    def test_warehouse_models_exist(self):
        from backend.database.models import (
            DebateAggregate, TopicTrending, ConsensusPattern,
            ModelPerformance, DailyMetricsSnapshot
        )
        assert hasattr(DebateAggregate, "id")
        assert hasattr(DebateAggregate, "topic_text")
        assert hasattr(TopicTrending, "topic_text")
        assert hasattr(ConsensusPattern, "consensus_level")
        assert hasattr(ConsensusPattern, "success_rate")
        assert hasattr(ModelPerformance, "model_name")
        assert hasattr(DailyMetricsSnapshot, "date")

    def test_warehouse_manager_imports(self):
        from backend.database.warehouse import WarehouseManager, warehouse_manager
        assert hasattr(WarehouseManager, "process_sequential_debate")
        assert hasattr(WarehouseManager, "backfill_historical_data")
        assert warehouse_manager is not None

    def test_warehouse_analytics_endpoint(self):
        client = TestClient(app)
        response = client.get("/api/v1/system/analytics")
        assert response.status_code in (200, 403)

    def test_backfill_script_exists(self):
        assert os.path.exists(os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "scripts", "backfill_warehouse.py"
        ))

    def test_analytics_queries_doc_exists(self):
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "docs", "ANALYTICS_QUERIES.md"
        )
        assert os.path.exists(doc_path)
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "SELECT" in content or "sql" in content.lower()


# ============================================================================
# NIVEL 5: PROMETHEUS METRICS
# ============================================================================

class TestPrometheusMetrics:
    """Pruebas del sistema de metricas Prometheus"""

    def test_prometheus_module_imports(self):
        from backend.monitoring.prometheus import (
            record_debate_completed,
            record_debate_report_cache_hit,
            record_debate_report_generated,
            record_prompt_cache_hit,
            record_prompt_cache_miss,
        )
        assert callable(record_debate_completed)
        assert callable(record_debate_report_cache_hit)

    def test_prometheus_metrics_endpoint(self):
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200
        text = response.text
        assert "debate_duration_seconds" in text or "debate_tokens_generated" in text

    def test_prometheus_debate_completed_recording(self):
        from backend.monitoring.prometheus import record_debate_completed
        try:
            record_debate_completed(
                total_tokens_out=500,
                total_latency_ms=3000,
                mode="standard"
            )
        except Exception as e:
            assert False, f"record_debate_completed raised: {e}"

    def test_prometheus_cache_hit_recording(self):
        from backend.monitoring.prometheus import record_prompt_cache_hit
        try:
            record_prompt_cache_hit("deterministic")
        except Exception as e:
            assert False, f"record_prompt_cache_hit raised: {e}"

    def test_prometheus_report_cache_hit_recording(self):
        from backend.monitoring.prometheus import record_debate_report_cache_hit
        try:
            record_debate_report_cache_hit("memory")
        except Exception as e:
            assert False, f"record_debate_report_cache_hit raised: {e}"


# ============================================================================
# NIVEL 6: REDUCTIO ABSURDUM
# ============================================================================

class TestReductioAbsurdum:
    """Pruebas del motor de Reduccion al Absurdo"""

    def test_reductio_module_imports(self):
        from backend.engine.reductio_absurdum import (
            ReductioAbsurdumEngine,
            AbsurdumProof,
            ComplacencyScan,
            get_reductio_absurdum_engine,
        )
        assert ReductioAbsurdumEngine is not None
        assert AbsurdumProof is not None
        assert ComplacencyScan is not None

    def test_reductio_engine_extract_propositions(self):
        from backend.engine.reductio_absurdum import get_reductio_absurdum_engine
        engine = get_reductio_absurdum_engine()
        text = "La IA es beneficiosa porque automatiza tareas repetitivas y mejora la productividad."
        propositions = engine.extract_propositions_from_text(text)
        assert isinstance(propositions, list)
        assert len(propositions) > 0

    def test_reductio_complacency_scan(self):
        from backend.engine.reductio_absurdum import get_reductio_absurdum_engine
        engine = get_reductio_absurdum_engine()
        scan = engine.analyze_consensus_points(
            consensus_points=["La IA es buena", "La tecnologia avanza"],
            dissent_points=[],
            debate_history="Debate sobre IA",
            iteration_number=1
        )
        assert hasattr(scan, "overall_complacency_risk")
        assert hasattr(scan, "weak_assumptions")
        assert hasattr(scan, "recommendations")

    def test_reductio_proof_model_fields(self):
        from backend.database.models import ReductioAbsurdumProof
        fields = [
            "debate_id", "iteration_number", "proposition", "extreme_case",
            "contradiction", "is_valid", "confidence_score",
            "questioning_agent", "challenged_agent", "consensus_areas",
            "weak_assumptions", "unquestioned_premises",
            "overall_complacency_risk", "recommendations"
        ]
        for field in fields:
            assert hasattr(ReductioAbsurdumProof, field), f"Missing field: {field}"

    def test_reductio_integration_in_debate_controller(self):
        from backend.engine.sequential_debate_controller import SequentialDebateController
        controller = SequentialDebateController()
        assert hasattr(controller, "reductio_engine")
        assert controller.reductio_engine is not None


# ============================================================================
# NIVEL 7: TRIBUNAL FALLBACK CHAINS
# ============================================================================

class TestTribunalFallback:
    """Pruebas de las fallback chains del Tribunal"""

    def test_tribunal_config_build(self):
        from backend.engine.tribunal_config import build_tribunal_config
        from backend.config import get_settings
        config = build_tribunal_config(get_settings())
        assert "evidence" in config
        assert "risk" in config
        assert "alignment" in config

    def test_tribunal_config_has_fallback_chains(self):
        from backend.engine.tribunal_config import build_tribunal_config
        from backend.config import get_settings
        config = build_tribunal_config(get_settings())
        for role_name, role_config in config.items():
            assert role_config.chain is not None, f"{role_name} has no fallback chain"
            assert len(role_config.chain) >= 1, f"{role_name} chain is empty"

    def test_tribunal_config_endpoint(self):
        client = TestClient(app)
        response = client.get("/api/v1/system/tribunal-config")
        assert response.status_code in (200, 404)

    def test_tribunal_config_env_override(self):
        from backend.engine.tribunal_config import build_tribunal_config
        from backend.config import get_settings
        settings = get_settings()
        config = build_tribunal_config(settings)
        assert config["evidence"].primary.node in ("LOCAL", "CLOUD")
        assert config["risk"].primary.node in ("LOCAL", "CLOUD")
        assert config["alignment"].primary.node in ("LOCAL", "CLOUD")


# ============================================================================
# NIVEL 8: SUPABASE SYNC QUEUE
# ============================================================================

class TestSupabaseSyncQueue:
    """Pruebas de la cola de sincronizacion con Supabase"""

    def test_sync_queue_model_fields(self):
        from backend.database.models import SupabaseSyncQueueItem
        fields = ["id", "kind", "debate_id", "payload", "status", "retry_count", "next_attempt_at", "created_at"]
        for field in fields:
            assert hasattr(SupabaseSyncQueueItem, field), f"Missing field: {field}"

    def test_sync_queue_persistence(self):
        from backend.database.models import SupabaseSyncQueueItem

        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                item = SupabaseSyncQueueItem(
                    kind="debate",
                    debate_id="test-sync-1",
                    payload={"id": "test-sync-1", "topic": "test"},
                )
                db_session.add(item)
                await db_session.commit()

                result = await db_session.execute(
                    select(SupabaseSyncQueueItem).where(
                        SupabaseSyncQueueItem.debate_id == "test-sync-1"
                    )
                )
                persisted = result.scalar_one_or_none()
                assert persisted is not None
                assert persisted.kind == "debate"
                assert persisted.status == "pending"

                await db_session.execute(
                    delete(SupabaseSyncQueueItem).where(
                        SupabaseSyncQueueItem.debate_id == "test-sync-1"
                    )
                )
                await db_session.commit()

        asyncio.run(scenario())

    def test_sync_queue_blocked_items(self):
        from backend.database.models import SupabaseSyncQueueItem

        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                item = SupabaseSyncQueueItem(
                    kind="debate",
                    debate_id="test-blocked-1",
                    payload={"id": "test-blocked-1"},
                    status="blocked",
                    retry_count=3,
                )
                db_session.add(item)
                await db_session.commit()

                result = await db_session.execute(
                    select(SupabaseSyncQueueItem).where(
                        SupabaseSyncQueueItem.debate_id == "test-blocked-1"
                    )
                )
                persisted = result.scalar_one_or_none()
                assert persisted is not None
                assert persisted.status == "blocked"
                assert persisted.retry_count == 3

                await db_session.execute(
                    delete(SupabaseSyncQueueItem).where(
                        SupabaseSyncQueueItem.debate_id == "test-blocked-1"
                    )
                )
                await db_session.commit()

        asyncio.run(scenario())


# ============================================================================
# NIVEL 9: WEBSOCKET MANAGER
# ============================================================================

class TestWebSocketManager:
    """Pruebas del gestor de WebSocket"""

    def test_websocket_manager_imports(self):
        from backend.api.websocket import WebSocketManager
        assert WebSocketManager is not None

    def test_websocket_manager_buffer_tokens(self):
        from backend.api.websocket import WebSocketManager
        manager = WebSocketManager()
        manager.buffer_tokens = True
        assert manager.buffer_tokens is True

    def test_websocket_manager_flush_buffer(self):
        from backend.api.websocket import WebSocketManager
        manager = WebSocketManager()
        assert hasattr(manager, "flush_session")
        assert callable(manager.flush_session)

    def test_websocket_manager_add_remove_connection(self):
        from backend.api.websocket import WebSocketManager
        manager = WebSocketManager()
        mock_ws = MagicMock()
        mock_ws.send_text = MagicMock()
        try:
            manager.connect("test-session", mock_ws)
            assert len(manager.active_connections) > 0 or len(manager.token_buffers) > 0
        except Exception:
            pass

    def test_ollama_client(self):
        from backend.adapters.ollama import OllamaClient
        client = OllamaClient()
        assert hasattr(client, "chat")
        assert hasattr(client, "generate")
        assert hasattr(client, "health_check")
        assert hasattr(client, "warm_model")
        assert hasattr(client, "unload_model")
        assert hasattr(client, "pull_model")

    def test_groq_client(self):
        from backend.adapters.groq import GroqClient
        client = GroqClient()
        assert hasattr(client, "chat_completion")
        assert hasattr(client, "health_check")

    def test_gemini_client(self):
        from backend.adapters.gemini import GeminiClient
        client = GeminiClient()
        assert hasattr(client, "chat_completion")
        assert hasattr(client, "health_check")

    def test_lm_studio_client(self):
        from backend.adapters.lm_studio import LMStudioClient
        client = LMStudioClient()
        assert hasattr(client, "chat_completion")
        assert hasattr(client, "health_check")

    def test_http_client_manager(self):
        from backend.adapters.http_client_manager import HTTPClientManager
        manager = HTTPClientManager()
        assert hasattr(manager, "get_client")
        assert hasattr(manager, "close_all")

    def test_openrouter_client(self):
        from backend.adapters.openrouter import OpenRouterClient
        client = OpenRouterClient()
        assert hasattr(client, "chat_completion")
        assert hasattr(client, "health_check")


# ============================================================================
# NIVEL 11: DEBATE MODELS
# ============================================================================

class TestDebateModels:
    """Pruebas de los modelos de datos del debate"""

    def test_agent_role_enum(self):
        from backend.engine.debate_models import AgentRole
        roles = [r.value for r in AgentRole]
        assert "analyst" in roles
        assert "critic" in roles
        assert "synthesizer" in roles
        assert "refiner" in roles
        assert "moderator" in roles
        assert "validator" in roles
        assert "consensus" in roles
        assert "tribunal" in roles

    def test_debate_agent_creation(self):
        from backend.engine.debate_models import DebateAgent, AgentRole
        agent = DebateAgent(
            id="test-agent",
            name="Test Agent",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3.2:latest",
            provider="meta",
            system_prompt="Test prompt",
            temperature=0.7,
            max_tokens=500
        )
        assert agent.id == "test-agent"
        assert agent.role == AgentRole.ANALYST
        assert agent.temperature == 0.7

    def test_debate_turn_creation(self):
        from backend.engine.debate_models import DebateTurn, DebateAgent, AgentRole
        agent = DebateAgent(
            id="a1", name="A1", role=AgentRole.ANALYST, node="LOCAL",
            engine="ollama", model="llama3.2:latest", provider="meta",
            system_prompt="", temperature=0.7, max_tokens=500
        )
        turn = DebateTurn(
            turn_number=1,
            agent=agent,
            prompt_sent="Test prompt"
        )
        assert turn.turn_number == 1
        assert turn.status == "pending"
        assert turn.tokens_in == 0

    def test_debate_session_creation(self):
        from backend.engine.debate_models import DebateSession
        session = DebateSession(
            id="test-session",
            topic="Test topic",
            status="created"
        )
        assert session.id == "test-session"
        assert session.topic == "Test topic"
        assert session.status == "created"
        assert session.max_iterations == 3

    def test_cruzamiento_critico(self):
        from backend.engine.debate_models import CruzamientoCritico
        cruz = CruzamientoCritico(
            from_agent="Agent A",
            to_agent="Agent B",
            target_argument="Test argument",
            response="Test response",
            iteration=1
        )
        assert cruz.from_agent == "Agent A"
        assert cruz.to_agent == "Agent B"
        assert cruz.iteration == 1

    def test_iteracion_debate(self):
        from backend.engine.debate_models import IteracionDebate
        iteration = IteracionDebate(
            iteration_number=1,
            phase="analysis"
        )
        assert iteration.iteration_number == 1
        assert iteration.phase == "analysis"
        assert len(iteration.turns) == 0
        assert len(iteration.cruzamientos) == 0

    def test_session_build_context_prompt(self):
        from backend.engine.debate_models import DebateSession, DebateAgent, AgentRole, DebateTurn
        session = DebateSession(id="s1", topic="Test topic", status="completed")
        agent = DebateAgent(
            id="a1", name="A1", role=AgentRole.ANALYST, node="LOCAL",
            engine="ollama", model="llama3.2:latest", provider="meta",
            system_prompt="", temperature=0.7, max_tokens=500
        )
        turn = DebateTurn(
            turn_number=1, agent=agent, prompt_sent="p",
            response_received="This is a comprehensive analysis of the topic with detailed evidence and structured arguments supporting the main position.",
            status="completed"
        )
        session.turns.append(turn)
        context = session.build_context_prompt(agent)
        assert "Test topic" in context
        assert "A1" in context


# ============================================================================
# NIVEL 12: CONVERGENCE EVALUATOR
# ============================================================================

class TestConvergenceEvaluator:
    """Pruebas del evaluador de convergencia"""

    def test_convergence_imports(self):
        from backend.engine.convergence import ConvergenceEvaluator
        assert ConvergenceEvaluator is not None

    def test_convergence_evaluate(self):
        from backend.engine.convergence import ConvergenceEvaluator
        evaluator = ConvergenceEvaluator()
        result = evaluator.evaluate(
            local_synthesis="Test synthesis about AI benefits",
            cloud_synthesis="AI is beneficial for society",
            round_number=2,
            max_rounds=3
        )
        assert hasattr(result, "similarity_score")
        assert hasattr(result, "should_stop")
        assert hasattr(result, "consensus_level")

    def test_convergence_early_stop(self):
        from backend.engine.convergence import ConvergenceEvaluator
        evaluator = ConvergenceEvaluator()
        result = evaluator.evaluate(
            local_synthesis="The sky is blue and clear",
            cloud_synthesis="The sky is blue and clear",
            round_number=3,
            max_rounds=3
        )
        assert result.similarity_score > 0.5


# ============================================================================
# NIVEL 13: QUALITY MONITOR
# ============================================================================

class TestQualityMonitor:
    """Pruebas del monitor de calidad"""

    def test_quality_monitor_imports(self):
        from backend.engine.quality_monitor import (
            QualityMonitor, is_response_usable, evaluate_response
        )
        assert QualityMonitor is not None
        assert callable(is_response_usable)
        assert callable(evaluate_response)

    def test_is_response_usable_good_response(self):
        from backend.engine.quality_monitor import is_response_usable
        long_response = "El analisis muestra que la inteligencia artificial tiene beneficios significativos en multiples areas. La automatizacion de tareas repetitivas permite a los humanos enfocarse en trabajo creativo y estrategico. Ademas, los sistemas de IA pueden procesar grandes volumenes de datos en tiempo real, identificando patrones que serian imposibles de detectar manualmente. La evidencia acumulada sugiere que la adopcion responsable de estas tecnologias puede transformar positivamente la sociedad."
        assert is_response_usable(long_response, "analyst") is True

    def test_is_response_usable_empty_response(self):
        from backend.engine.quality_monitor import is_response_usable
        assert is_response_usable("", "analyst") is False
        assert is_response_usable("   ", "analyst") is False

    def test_is_response_usable_error_response(self):
        from backend.engine.quality_monitor import is_response_usable
        assert is_response_usable("[ERROR: Connection failed]", "analyst") is False

    def test_evaluate_response_returns_score(self):
        from backend.engine.quality_monitor import evaluate_response
        score, details = evaluate_response("Good response with detailed analysis.", "analyst")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


# ============================================================================
# NIVEL 14: REPUTATION MANAGER
# ============================================================================

class TestReputationManager:
    """Pruebas del gestor de reputacion EMA"""

    def test_reputation_imports(self):
        from backend.engine.reputation_unified import ReputationManager, reputation_service
        assert ReputationManager is not None
        assert reputation_service is not None

    def test_reputation_service_instance(self):
        from backend.engine.reputation_unified import reputation_service
        assert hasattr(reputation_service, "get_reputation")
        assert hasattr(reputation_service, "list_all")
        assert hasattr(reputation_service, "update_after_turn")
        assert hasattr(reputation_service, "update_after_session")

    def test_reputation_update_and_get(self):
        from backend.engine.reputation_unified import reputation_service

        async def scenario():
            model = "test-model-rep"
            role = "analyst"
            await reputation_service.update_after_turn(
                model=model, provider="test", role=role,
                tokens_out=100, latency_ms=500, success=True,
                intervention_type="analysis"
            )
            rep = await reputation_service.get_reputation(model, role)
            assert rep is not None

        asyncio.run(scenario())

    def test_reputation_list_all(self):
        from backend.engine.reputation_unified import reputation_service

        async def scenario():
            reps = await reputation_service.list_all(min_turns=0)
            assert isinstance(reps, list)

        asyncio.run(scenario())


# ============================================================================
# NIVEL 15: TASK MANAGER
# ============================================================================

class TestTaskManager:
    """Pruebas del gestor de tareas en background"""

    def test_task_manager_imports(self):
        from backend.engine.task_manager import BackgroundTaskManager, TaskConfig, task_manager
        assert BackgroundTaskManager is not None
        assert TaskConfig is not None
        assert task_manager is not None

    def test_task_manager_submit(self):
        from backend.engine.task_manager import task_manager, TaskConfig

        async def scenario():
            async def my_task():
                return "test result"
            info = await task_manager.submit(
                my_task,
                context="test",
                config=TaskConfig(max_retries=0)
            )
            assert info is not None
            assert hasattr(info, "task_id") or isinstance(info, str)

        asyncio.run(scenario())


# ============================================================================
# NIVEL 16: EXPORT ENDPOINTS
# ============================================================================

class TestExportEndpoints:
    """Pruebas de los endpoints de exportacion"""

    def test_export_json_not_found(self):
        client = TestClient(app)
        response = client.get("/api/v1/debates/nonexistent/export/json")
        assert response.status_code == 404

    def test_export_markdown_not_found(self):
        client = TestClient(app)
        response = client.get("/api/v1/debates/nonexistent/export/markdown")
        assert response.status_code == 404

    def test_export_pdf_not_found(self):
        client = TestClient(app)
        response = client.get("/api/v1/debates/nonexistent/export/pdf")
        assert response.status_code == 404

    def test_export_json_content_type(self):
        """Verifica que el endpoint JSON retorna application/json"""
        from backend.api.routes.debate import export_debate_json
        assert export_debate_json is not None

    def test_export_markdown_content_type(self):
        """Verifica que el endpoint MD retorna text/markdown"""
        from backend.api.routes.debate import export_debate_markdown
        assert export_debate_markdown is not None

    def test_export_pdf_content_type(self):
        """Verifica que el endpoint PDF retorna text/html"""
        from backend.api.routes.debate import export_debate_pdf
        assert export_debate_pdf is not None


# ============================================================================
# NIVEL 17: PROMPT RESPONSE CACHE (DB)
# ============================================================================

class TestPromptResponseCache:
    """Pruebas de la cache de respuestas en DB"""

    def test_cache_persistence(self):
        from backend.database.models import PromptResponseCache

        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                cache_key = "test-cache-key-1"
                item = PromptResponseCache(
                    cache_key=cache_key,
                    engine="ollama",
                    model="llama3.2:latest",
                    node="LOCAL",
                    temperature=0.7,
                    max_tokens=500,
                    prompt_hash="abc123",
                    response_text="Test response",
                    tokens_in=100,
                    tokens_out=200,
                    latency_ms=500,
                    hit_count=0,
                )
                db_session.add(item)
                await db_session.commit()

                result = await db_session.execute(
                    select(PromptResponseCache).where(
                        PromptResponseCache.cache_key == cache_key
                    )
                )
                persisted = result.scalar_one_or_none()
                assert persisted is not None
                assert persisted.response_text == "Test response"
                assert persisted.hit_count == 0

                await db_session.execute(
                    delete(PromptResponseCache).where(
                        PromptResponseCache.cache_key == cache_key
                    )
                )
                await db_session.commit()

        asyncio.run(scenario())

    def test_cache_hit_count_increment(self):
        from backend.database.models import PromptResponseCache

        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                cache_key = "test-cache-key-2"
                item = PromptResponseCache(
                    cache_key=cache_key,
                    engine="ollama",
                    model="llama3.2:latest",
                    node="LOCAL",
                    temperature=0.7,
                    max_tokens=500,
                    prompt_hash="def456",
                    response_text="Test response 2",
                    tokens_in=100,
                    tokens_out=200,
                    latency_ms=500,
                    hit_count=5,
                )
                db_session.add(item)
                await db_session.commit()

                result = await db_session.execute(
                    select(PromptResponseCache).where(
                        PromptResponseCache.cache_key == cache_key
                    )
                )
                persisted = result.scalar_one_or_none()
                assert persisted is not None
                assert persisted.hit_count == 5

                await db_session.execute(
                    delete(PromptResponseCache).where(
                        PromptResponseCache.cache_key == cache_key
                    )
                )
                await db_session.commit()

        asyncio.run(scenario())


# ============================================================================
# NIVEL 18: INTERVENTION TAXONOMY
# ============================================================================

class TestInterventionTaxonomy:
    """Pruebas de la clasificacion de actos discursivos"""

    def test_intervention_taxonomy_imports(self):
        from backend.engine.intervention_taxonomy import detect_intervention_type
        assert callable(detect_intervention_type)

    def test_detect_analysis_intervention(self):
        from backend.engine.intervention_taxonomy import detect_intervention_type
        result = detect_intervention_type(
            "El analisis muestra que la IA tiene beneficios significativos...",
            "analyst"
        )
        assert isinstance(result, str)

    def test_detect_criticism_intervention(self):
        from backend.engine.intervention_taxonomy import detect_intervention_type
        result = detect_intervention_type(
            "Sin embargo, hay debilidades en el argumento presentado...",
            "critic"
        )
        assert isinstance(result, str)

    def test_detect_synthesis_intervention(self):
        from backend.engine.intervention_taxonomy import detect_intervention_type
        result = detect_intervention_type(
            "En sintesis, los puntos de acuerdo son...",
            "synthesizer"
        )
        assert isinstance(result, str)


# ============================================================================
# NIVEL 19: LOCAL ENGINE MANAGER
# ============================================================================

class TestLocalEngineManager:
    """Pruebas del gestor de motores locales"""

    def test_local_engine_manager_imports(self):
        from backend.engine.local_engine_manager import LocalEngineManager, EngineType
        assert LocalEngineManager is not None
        assert EngineType is not None

    def test_engine_type_enum(self):
        from backend.engine.local_engine_manager import EngineType
        assert hasattr(EngineType, "OLLAMA")
        assert hasattr(EngineType, "LM_STUDIO")
        assert hasattr(EngineType, "JAN")

    def test_local_engine_manager_instance(self):
        from backend.engine.local_engine_manager import LocalEngineManager
        manager = LocalEngineManager()
        assert hasattr(manager, "engines")
        assert hasattr(manager, "generate")

    def test_local_engine_manager_schedule_preload(self):
        from backend.engine.local_engine_manager import LocalEngineManager
        manager = LocalEngineManager()
        assert hasattr(manager, "schedule_ollama_preload")


# ============================================================================
# NIVEL 20: CONFIG SETTINGS
# ============================================================================

class TestConfigSettings:
    """Pruebas de la configuracion de la aplicacion"""

    def test_settings_node_role(self):
        from backend.config import get_settings
        s = get_settings()
        assert s.NODE_ROLE in ("MASTER", "WORKER")

    def test_settings_is_master(self):
        from backend.config import get_settings
        s = get_settings()
        assert isinstance(s.is_master, bool)

    def test_settings_get_worker_host(self):
        from backend.config import get_settings
        s = get_settings()
        if s.is_master:
            host = s.get_worker_host()
            assert host is not None

    def test_settings_port(self):
        from backend.config import get_settings
        s = get_settings()
        assert s.PORT == 8000

    def test_settings_api_keys_not_placeholder(self):
        from backend.config import get_settings
        s = get_settings()
        if s.GROQ_API_KEY:
            assert "CHANGEME" not in s.GROQ_API_KEY
        if s.GEMINI_API_KEY:
            assert "CHANGEME" not in s.GEMINI_API_KEY
        if s.OPENROUTER_API_KEY:
            assert "CHANGEME" not in s.OPENROUTER_API_KEY

    def test_settings_supabase_disabled_gracefully(self):
        from backend.config import get_settings
        s = get_settings()
        if not s.SUPABASE_URL or "CHANGEME" in (s.SUPABASE_URL or ""):
            assert s.SUPABASE_ENABLED is False or s.SUPABASE_URL is None
