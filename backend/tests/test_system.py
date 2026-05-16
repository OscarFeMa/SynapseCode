"""
Synapse Council - Tests de integracion y importacion
Ejecutar: pytest backend/tests/ -v
"""
import sys, os
import asyncio
import json
import uuid
from unittest.mock import AsyncMock
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
        assert app.title == "Synapse Council v2.0"
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

    def test_prometheus_metrics_endpoint_exposes_core_metrics(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        client.get("/health/live")
        r = client.get("/metrics")

        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]
        body = r.text
        assert "synapse_http_requests_total" in body
        assert "synapse_http_request_duration_seconds" in body
        assert "synapse_debate_reports_generated_total" in body
        assert "synapse_prompt_cache_hits_total" in body
        assert "synapse_prompt_cache_misses_total" in body
        assert "synapse_supabase_sync_failures_total" in body
        assert "synapse_supabase_sync_retries_total" in body
        assert "synapse_warehouse_debates_aggregated_total" in body
        assert 'path="/health/live"' in body

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

    def test_report_is_generated_from_completed_db_debate_when_missing(self, monkeypatch):
        from backend.main import app
        from fastapi.testclient import TestClient
        from backend.api.routes import debate as debate_routes

        session_id = "completed-db-debate"

        monkeypatch.setattr(
            debate_routes.debate_controller,
            "get_session",
            lambda _: None
        )
        monkeypatch.setattr(
            debate_routes.debate_controller,
            "get_debate_from_db",
            AsyncMock(return_value={
                "id": session_id,
                "topic": "Impacto de la IA en educacion",
                "status": "completed",
                "structured_report": None,
                "turns": [
                    {
                        "turn_number": 1,
                        "agent_name": "Analyst",
                        "agent_role": "analyst",
                        "model": "llama3.2:latest",
                        "provider": "meta",
                        "node": "LOCAL",
                        "response_preview": "La IA acelera la personalizacion.",
                        "response_received": "La IA acelera la personalizacion del aprendizaje.",
                        "tokens_in": 10,
                        "tokens_out": 12,
                        "latency_ms": 100,
                        "status": "completed",
                    }
                ],
            })
        )
        monkeypatch.setattr(
            debate_routes.debate_controller,
            "generate_structured_report_for_debate",
            AsyncMock(return_value={
                "summary": "Resumen regenerado",
                "consensus_level": 70,
                "key_findings": ["La IA personaliza el aprendizaje"],
                "risks_identified": [],
                "action_items": [],
                "generated_by": "report_cache_backfill",
            }),
            raising=False,
        )

        client = TestClient(app)
        response = client.get(f"/api/v1/debates/{session_id}/report")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["source"] == "database_generated"
        assert data["structured_report"]["summary"] == "Resumen regenerado"

    def test_reductio_proof_is_persisted_with_scan_metadata(self):
        from sqlalchemy import select, delete
        from backend.database.local_db import init_db, AsyncSessionLocal
        from backend.database.models import SequentialDebate, ReductioAbsurdumProof
        from backend.engine.sequential_debate_controller import SequentialDebateController
        from backend.engine.reductio_absurdum import AbsurdumProof as RuntimeAbsurdumProof, ComplacencyScan

        debate_id = f"reductio-{uuid.uuid4()}"

        async def scenario():
            await init_db()

            async with AsyncSessionLocal() as db_session:
                db_session.add(
                    SequentialDebate(
                        id=debate_id,
                        topic="Debate de prueba reductio",
                        status="completed",
                        total_turns=2,
                    )
                )
                await db_session.commit()

            controller = SequentialDebateController()
            scan = ComplacencyScan(
                consensus_areas=["La automatizacion siempre mejora la calidad"],
                weak_assumptions=["La automatizacion siempre mejora la calidad"],
                unquestioned_premises=["Siempre implica menos errores"],
                overall_complacency_risk=0.82,
                recommendations=["Desafiar absolutos en automatizacion"],
            )
            proof = RuntimeAbsurdumProof(
                proposition="La automatizacion siempre mejora la calidad",
                extreme_case="Si se automatiza toda decision sin revision humana, aparecen errores sistemicos.",
                contradiction="Esto contradice la necesidad de supervisar excepciones complejas.",
                is_valid=False,
                confidence_score=0.8,
                questioning_agent="Critic",
                challenged_agent="Analyst",
            )

            await controller._persist_reductio_absurdum_proof(
                debate_id=debate_id,
                iteration_number=2,
                complacency_scan=scan,
                proof=proof,
            )

            async with AsyncSessionLocal() as db_session:
                result = await db_session.execute(
                    select(ReductioAbsurdumProof).where(ReductioAbsurdumProof.debate_id == debate_id)
                )
                record = result.scalar_one()

            assert record.iteration_number == 2
            assert record.proposition == proof.proposition
            assert record.questioning_agent == "Critic"
            assert record.challenged_agent == "Analyst"
            assert record.overall_complacency_risk == 0.82
            assert record.weak_assumptions == ["La automatizacion siempre mejora la calidad"]
            assert record.recommendations == ["Desafiar absolutos en automatizacion"]
            assert record.is_valid is False

            async with AsyncSessionLocal() as db_session:
                await db_session.execute(
                    delete(ReductioAbsurdumProof).where(ReductioAbsurdumProof.debate_id == debate_id)
                )
                await db_session.execute(
                    delete(SequentialDebate).where(SequentialDebate.id == debate_id)
                )
                await db_session.commit()

        asyncio.run(scenario())

    def test_export_json_includes_structured_metadata(self, monkeypatch):
        from datetime import datetime, timedelta
        from backend.main import app
        from fastapi.testclient import TestClient
        from backend.api.routes import debate as debate_routes
        from backend.engine.debate_models import (
            DebateSession,
            DebateTurn,
            DebateAgent,
            AgentRole,
            IteracionDebate,
            CruzamientoCritico,
        )

        analyst = DebateAgent(
            id="a1",
            name="Analyst",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3.2:latest",
            provider="meta",
            system_prompt="",
        )
        critic = DebateAgent(
            id="a2",
            name="Critic",
            role=AgentRole.CRITIC,
            node="LOCAL",
            engine="ollama",
            model="mistral:latest",
            provider="mistral",
            system_prompt="",
        )

        created_at = datetime.now()
        completed_at = created_at + timedelta(seconds=12)

        turn_1 = DebateTurn(
            turn_number=1,
            agent=analyst,
            prompt_sent="",
            response_received="La IA mejora la trazabilidad.",
            tokens_out=120,
            latency_ms=800,
            status="completed",
        )
        turn_2 = DebateTurn(
            turn_number=2,
            agent=critic,
            prompt_sent="",
            response_received="Tambien puede amplificar errores si no hay supervision.",
            tokens_out=140,
            latency_ms=950,
            status="completed",
        )

        iteration = IteracionDebate(
            iteration_number=1,
            phase="analysis",
            turns=[turn_1, turn_2],
            consensus_points=["La IA necesita supervision"],
            disagreement_points=["El grado de autonomia aceptable"],
        )
        iteration.cruzamientos.append(
            CruzamientoCritico(
                from_agent="Critic",
                to_agent="Analyst",
                target_argument="La IA mejora la trazabilidad.",
                response="Eso depende de controles humanos robustos.",
                iteration=1,
            )
        )

        session = DebateSession(
            id="export-structured-1",
            topic="Impacto de la IA en auditoria",
            turns=[turn_1, turn_2],
            iterations=[iteration],
            status="completed",
            created_at=created_at,
            completed_at=completed_at,
            final_verdict="Adoptar IA con supervision humana.",
            structured_report={
                "summary": "Resumen estructurado",
                "consensus_level": 72,
            },
        )

        monkeypatch.setattr(
            debate_routes.debate_controller,
            "get_session",
            lambda session_id: session if session_id == session.id else None
        )

        client = TestClient(app)
        response = client.get(f"/api/v1/debates/{session.id}/export/json")

        assert response.status_code == 200
        data = response.json()
        assert data["debate_id"] == session.id
        assert data["topic"] == session.topic
        assert data["structured_report"]["summary"] == "Resumen estructurado"
        assert data["summary"]["completed_turns"] == 2
        assert data["iterations"][0]["number"] == 1
        assert data["iterations"][0]["consensus_points"] == ["La IA necesita supervision"]
        assert data["iterations"][0]["dissent_areas"] == ["El grado de autonomia aceptable"]
        assert data["iterations"][0]["cross_references"][0]["from_agent"] == "Critic"

    def test_websocket_manager_buffers_token_events(self):
        from backend.api.websocket import WebSocketManager

        class FakeWebSocket:
            def __init__(self):
                self.messages = []

            async def send_text(self, message):
                self.messages.append(message)

        async def scenario():
            manager = WebSocketManager()
            ws = FakeWebSocket()
            session_id = "ws-buffer-test"
            manager.active_connections[session_id] = {ws}

            await manager.send_event(session_id, "tribunal_token", {"role": "risk", "token": "Hola"})
            await manager.send_event(session_id, "tribunal_token", {"role": "risk", "token": " mundo"})
            await manager.flush_session(session_id)

            assert len(ws.messages) == 1
            payload = json.loads(ws.messages[0])
            assert payload["type"] == "tribunal_token_batch"
            assert payload["payload"]["role"] == "risk"
            assert payload["payload"]["token"] == "Hola mundo"
            assert payload["payload"]["token_count"] == 2

        asyncio.run(scenario())

    def test_controller_schedules_preload_for_next_local_ollama_model(self):
        from backend.engine.sequential_debate_controller import SequentialDebateController
        from backend.engine.debate_models import DebateAgent, AgentRole

        controller = SequentialDebateController()

        agents = [
            DebateAgent(
                id="a1",
                name="Agent 1",
                role=AgentRole.ANALYST,
                node="LOCAL",
                engine="ollama",
                model="llama3.2:latest",
                provider="meta",
                system_prompt="",
            ),
            DebateAgent(
                id="a2",
                name="Agent 2",
                role=AgentRole.CRITIC,
                node="LOCAL",
                engine="ollama",
                model="mistral:latest",
                provider="mistral",
                system_prompt="",
            ),
            DebateAgent(
                id="a3",
                name="Agent 3",
                role=AgentRole.SYNTHESIZER,
                node="CLOUD",
                engine="openrouter",
                model="openai/gpt-4o-mini",
                provider="openai",
                system_prompt="",
            ),
        ]

        assert controller._find_next_preload_model(agents, current_index=0) == "mistral:latest"
        assert controller._find_next_preload_model(agents, current_index=1) is None

    def test_local_agent_uses_deterministic_response_cache(self):
        from sqlalchemy import delete
        from backend.database.local_db import init_db, AsyncSessionLocal
        from backend.database.models import PromptResponseCache
        from backend.engine.sequential_debate_controller import SequentialDebateController
        from backend.engine.debate_models import DebateAgent, AgentRole

        agent = DebateAgent(
            id="cache-agent",
            name="Cache Agent",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3.2:latest",
            provider="meta",
            system_prompt="",
            temperature=0.3,
            max_tokens=128,
        )

        async def scenario():
            await init_db()
            controller = SequentialDebateController()
            call_counter = {"count": 0}

            async def fake_generate(**kwargs):
                call_counter["count"] += 1
                for token in ["Hola", " mundo"]:
                    yield token

            controller.local_manager.generate = fake_generate
            prompt = "Explica por que la cache reduce latencia."

            first = await controller._run_local_agent(agent, prompt)
            second = await controller._run_local_agent(agent, prompt)

            assert first["text"] == "Hola mundo"
            assert second["text"] == "Hola mundo"
            assert second["cache_hit"] is True
            assert call_counter["count"] == 1

            async with AsyncSessionLocal() as db_session:
                await db_session.execute(
                    delete(PromptResponseCache).where(PromptResponseCache.model == agent.model)
                )
                await db_session.commit()

        asyncio.run(scenario())

    def test_sqlite_migration_upgrades_legacy_prompt_cache_schema(self):
        from sqlalchemy import create_engine, text
        from backend.database.migrations.sqlite_migrations import run_sqlite_migrations

        engine = create_engine("sqlite:///:memory:")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE prompt_response_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cache_key VARCHAR(64) NOT NULL UNIQUE,
                        engine VARCHAR(20) NOT NULL,
                        model VARCHAR(100) NOT NULL,
                        node VARCHAR(20) NOT NULL,
                        temperature FLOAT NOT NULL DEFAULT 0.0,
                        max_tokens INTEGER,
                        prompt_hash VARCHAR(64) NOT NULL,
                        response_text TEXT NOT NULL,
                        tokens_in INTEGER NOT NULL DEFAULT 0,
                        tokens_out INTEGER NOT NULL DEFAULT 0,
                        latency_ms INTEGER NOT NULL DEFAULT 0,
                        hit_count INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        last_accessed_at DATETIME NOT NULL
                    )
                    """
                )
            )

            run_sqlite_migrations(conn)
            run_sqlite_migrations(conn)

            columns = {
                row._mapping["name"]
                for row in conn.execute(text("PRAGMA table_info(prompt_response_cache)"))
            }
            indexes = {
                row._mapping["name"]
                for row in conn.execute(text("PRAGMA index_list(prompt_response_cache)"))
            }

        assert {"prompt_embedding", "similarity_threshold", "expires_at"} <= columns
        assert "idx_prompt_cache_expires" in indexes

    def test_warehouse_processes_sequential_debate_idempotently(self):
        from datetime import datetime, UTC
        from sqlalchemy import delete, select
        from backend.database.local_db import init_db, AsyncSessionLocal
        from backend.database.models import (
            DailyMetricsSnapshot,
            DebateAggregate,
            ModelPerformance,
            SequentialDebate,
            SequentialDebateTurn,
            TopicTrending,
        )
        from backend.database.warehouse import WarehouseManager

        debate_id = f"warehouse-{uuid.uuid4()}"
        topic = f"Warehouse topic {uuid.uuid4()}"
        model_name = f"warehouse-model-{uuid.uuid4()}"
        completed_at = datetime(2099, 1, 2, 12, 0, tzinfo=UTC)
        created_at = datetime(2099, 1, 2, 11, 59, tzinfo=UTC)

        async def scenario():
            await init_db()
            manager = WarehouseManager()
            topic_hash = manager._hash_topic(topic)

            async with AsyncSessionLocal() as db_session:
                await db_session.execute(delete(TopicTrending).where(TopicTrending.topic_hash == topic_hash))
                await db_session.execute(delete(DebateAggregate).where(DebateAggregate.id == debate_id))
                await db_session.execute(delete(DailyMetricsSnapshot).where(DailyMetricsSnapshot.date == "2099-01-02"))
                await db_session.execute(delete(ModelPerformance).where(ModelPerformance.model_name == model_name))
                await db_session.execute(delete(SequentialDebateTurn).where(SequentialDebateTurn.debate_id == debate_id))
                await db_session.execute(delete(SequentialDebate).where(SequentialDebate.id == debate_id))
                db_session.add(
                    SequentialDebate(
                        id=debate_id,
                        topic=topic,
                        mode="standard",
                        status="completed",
                        total_turns=2,
                        total_tokens_in=30,
                        total_tokens_out=70,
                        total_latency_ms=1500,
                        created_at=created_at,
                        completed_at=completed_at,
                    )
                )
                db_session.add_all([
                    SequentialDebateTurn(
                        debate_id=debate_id,
                        turn_number=1,
                        agent_id="a1",
                        agent_name="Analyst",
                        agent_role="analyst",
                        model=model_name,
                        provider="local",
                        node="LOCAL",
                        engine="ollama",
                        prompt_sent="p1",
                        response_received="r1",
                        tokens_in=10,
                        tokens_out=20,
                        latency_ms=500,
                        status="completed",
                    ),
                    SequentialDebateTurn(
                        debate_id=debate_id,
                        turn_number=2,
                        agent_id="a2",
                        agent_name="Critic",
                        agent_role="critic",
                        model=model_name,
                        provider="local",
                        node="LOCAL",
                        engine="ollama",
                        prompt_sent="p2",
                        response_received="r2",
                        tokens_in=20,
                        tokens_out=50,
                        latency_ms=1000,
                        status="completed",
                    ),
                ])
                await db_session.commit()

            assert await manager.process_sequential_debate(debate_id) is True
            assert await manager.process_sequential_debate(debate_id) is True

            async with AsyncSessionLocal() as db_session:
                aggregate = await db_session.get(DebateAggregate, debate_id)
                topic_row = (
                    await db_session.execute(
                        select(TopicTrending).where(TopicTrending.topic_hash == topic_hash)
                    )
                ).scalar_one()
                daily = (
                    await db_session.execute(
                        select(DailyMetricsSnapshot).where(DailyMetricsSnapshot.date == "2099-01-02")
                    )
                ).scalar_one()
                model_rows = (
                    await db_session.execute(
                        select(ModelPerformance).where(ModelPerformance.model_name == model_name)
                    )
                ).scalars().all()

                assert aggregate.duration_seconds == 60
                assert aggregate.unique_models_count == 1
                assert topic_row.debate_count == 1
                assert topic_row.total_turns == 2
                assert daily.total_debates_completed == 1
                assert daily.total_tokens_generated == 70
                assert len(model_rows) == 2
                assert {row.agent_role for row in model_rows} == {"analyst", "critic"}

                await db_session.execute(delete(TopicTrending).where(TopicTrending.topic_hash == topic_hash))
                await db_session.execute(delete(DailyMetricsSnapshot).where(DailyMetricsSnapshot.date == "2099-01-02"))
                await db_session.execute(delete(ModelPerformance).where(ModelPerformance.model_name == model_name))
                await db_session.execute(delete(DebateAggregate).where(DebateAggregate.id == debate_id))
                await db_session.execute(delete(SequentialDebateTurn).where(SequentialDebateTurn.debate_id == debate_id))
                await db_session.execute(delete(SequentialDebate).where(SequentialDebate.id == debate_id))
                await db_session.commit()

        asyncio.run(scenario())

    def test_system_analytics_endpoint_returns_warehouse_summary(self, monkeypatch):
        from datetime import datetime, UTC
        from sqlalchemy import delete
        from backend.main import app
        from backend.api.routes import system as system_routes
        from fastapi.testclient import TestClient
        from backend.database.local_db import init_db, AsyncSessionLocal
        from backend.database.models import DailyMetricsSnapshot, ModelPerformance, TopicTrending

        topic_hash = f"analytics-topic-{uuid.uuid4()}"
        model_name = f"analytics-model-{uuid.uuid4()}"

        async def seed():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                await db_session.execute(delete(TopicTrending).where(TopicTrending.topic_hash == topic_hash))
                await db_session.execute(delete(ModelPerformance).where(ModelPerformance.model_name == model_name))
                await db_session.execute(delete(DailyMetricsSnapshot).where(DailyMetricsSnapshot.date == "2099-02-03"))
                db_session.add(
                    DailyMetricsSnapshot(
                        date="2099-02-03",
                        total_debates_completed=3,
                        total_turns_executed=9,
                        total_tokens_generated=1234,
                        unique_topics_count=1,
                        active_models_count=2,
                    )
                )
                db_session.add(
                    TopicTrending(
                        date="2099-02-03",
                        topic_hash=topic_hash,
                        topic_text="Analytics topic",
                        debate_count=3,
                        total_turns=9,
                        unique_models_count=2,
                    )
                )
                db_session.add(
                    ModelPerformance(
                        model_name=model_name,
                        provider="local",
                        engine="ollama",
                        agent_role="analyst",
                        total_turns=5,
                        avg_tokens_out=80.0,
                        avg_latency_ms=900.0,
                        success_rate=1.0,
                        last_updated=datetime(2099, 2, 3, tzinfo=UTC),
                    )
                )
                await db_session.commit()

        async def cleanup():
            async with AsyncSessionLocal() as db_session:
                await db_session.execute(delete(TopicTrending).where(TopicTrending.topic_hash == topic_hash))
                await db_session.execute(delete(ModelPerformance).where(ModelPerformance.model_name == model_name))
                await db_session.execute(delete(DailyMetricsSnapshot).where(DailyMetricsSnapshot.date == "2099-02-03"))
                await db_session.commit()

        asyncio.run(seed())
        try:
            monkeypatch.setattr(system_routes.settings, "ADMIN_API_LOCALHOST_ONLY", False)
            client = TestClient(app)
            response = client.get("/api/v1/system/analytics?limit=1")

            assert response.status_code == 200
            data = response.json()
            assert data["dailySummary"]["date"] == "2099-02-03"
            assert data["dailySummary"]["totalDebatesCompleted"] == 3
            assert data["topTopics"][0]["topicHash"] == topic_hash
            assert data["modelLeaderboard"][0]["model"] == model_name
        finally:
            asyncio.run(cleanup())

    def test_sync_health_reports_blocked_queue(self, monkeypatch):
        from datetime import datetime, timedelta
        from sqlalchemy import delete
        from backend.main import app
        from backend.api.routes import system as system_routes
        from fastapi.testclient import TestClient
        from backend.database.local_db import init_db, AsyncSessionLocal
        from backend.database.models import SupabaseSyncQueueItem
        from backend.memory.hybrid_memory_v2 import get_hybrid_memory_v2

        debate_id = f"sync-health-{uuid.uuid4()}"

        async def seed():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                await db_session.execute(
                    delete(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == debate_id)
                )
                db_session.add(
                    SupabaseSyncQueueItem(
                        kind="debate",
                        debate_id=debate_id,
                        payload={"id": debate_id, "topic": "sync health"},
                        status="pending",
                        retry_count=2,
                        last_error="network down",
                        next_attempt_at=datetime.now() - timedelta(seconds=1),
                    )
                )
                await db_session.commit()

        async def cleanup():
            async with AsyncSessionLocal() as db_session:
                await db_session.execute(
                    delete(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == debate_id)
                )
                await db_session.commit()

        memory = get_hybrid_memory_v2()
        original_enabled = memory.supabase.enabled
        asyncio.run(seed())
        try:
            monkeypatch.setattr(system_routes.settings, "ADMIN_API_LOCALHOST_ONLY", False)
            monkeypatch.setattr(memory.supabase, "enabled", True)

            client = TestClient(app)
            response = client.get("/api/v1/system/health/sync")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "blocked"
            assert data["queue"]["pending"] >= 1
            assert data["queue"]["withRetries"] >= 1
            assert data["queue"]["dueNow"] >= 1
            assert data["queue"]["lastError"]["debateId"] == debate_id
            assert "revisa" in data["recommendation"].lower()
        finally:
            memory.supabase.enabled = original_enabled
            asyncio.run(cleanup())

    def test_hybrid_memory_persists_sync_queue_item_on_failure(self):
        from sqlalchemy import select, delete
        from backend.database.local_db import init_db, AsyncSessionLocal
        from backend.memory.hybrid_memory_v2 import HybridMemoryV2
        from backend.database.models import SupabaseSyncQueueItem
        from backend.monitoring.prometheus import render_prometheus_metrics
        from backend.engine.debate_models import DebateSession

        async def scenario():
            await init_db()
            memory = HybridMemoryV2()
            memory._enabled = True

            class FakeSupabase:
                async def sync_debate(self, data):
                    return {"synced": False, "error": "network down"}

            memory.supabase = FakeSupabase()

            session = DebateSession(
                id="sync-queue-1",
                topic="Persistencia de cola",
                status="completed",
            )

            await memory.enqueue_sync(session, session.id, "standard")
            item = await memory.dequeue_persistent_item()
            assert item is not None

            processed = await memory.process_persistent_item(item)
            assert processed is False
            metrics = render_prometheus_metrics()
            assert "synapse_supabase_sync_failures_total" in metrics
            assert "synapse_supabase_sync_retries_total" in metrics

            async with AsyncSessionLocal() as db_session:
                result = await db_session.execute(
                    select(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == session.id)
                )
                persisted = result.scalar_one()
                assert persisted.status == "pending"
                assert persisted.retry_count == 1

                await db_session.execute(
                    delete(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == session.id)
                )
                await db_session.commit()

        asyncio.run(scenario())

    def test_hybrid_memory_rehydrates_pending_queue_items_on_start(self):
        from sqlalchemy import delete
        from backend.database.local_db import init_db, AsyncSessionLocal
        from backend.memory.hybrid_memory_v2 import HybridMemoryV2
        from backend.database.models import SupabaseSyncQueueItem

        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                db_session.add(
                    SupabaseSyncQueueItem(
                        kind="debate",
                        debate_id="rehydrate-1",
                        payload={"id": "rehydrate-1", "topic": "rehydrate"},
                    )
                )
                await db_session.commit()

            memory = HybridMemoryV2()
            memory._enabled = True
            await memory._rehydrate_pending_queue()

            assert memory._queue.qsize() >= 1

            async with AsyncSessionLocal() as db_session:
                await db_session.execute(
                    delete(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == "rehydrate-1")
                )
                await db_session.commit()

        asyncio.run(scenario())
