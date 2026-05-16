"""
API tests for debate endpoints
"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from backend.main import app


class TestDebateEndpoints:
    """Pruebas de endpoints de debates"""

    def test_debate_list_shape(self):
        client = TestClient(app)
        r = client.get("/api/v1/debates/list")
        assert r.status_code == 200
        data = r.json()
        assert "count" in data
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_create_debate_invalid(self):
        client = TestClient(app)
        r = client.post("/api/v1/debates/create", json={})
        assert r.status_code in (400, 422)

    def test_report_is_generated_from_completed_db_debate_when_missing(
        self, monkeypatch
    ):
        from unittest.mock import AsyncMock

        from backend.api.routes import debate as debate_routes

        session_id = "completed-db-debate"
        monkeypatch.setattr(
            debate_routes.debate_controller, "get_session", lambda _: None
        )
        monkeypatch.setattr(
            debate_routes.debate_controller,
            "get_debate_from_db",
            AsyncMock(
                return_value={
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
                }
            ),
        )
        monkeypatch.setattr(
            debate_routes.debate_controller,
            "generate_structured_report_for_debate",
            AsyncMock(
                return_value={
                    "summary": "Resumen regenerado",
                    "consensus_level": 70,
                    "key_findings": ["La IA personaliza el aprendizaje"],
                    "risks_identified": [],
                    "action_items": [],
                    "generated_by": "report_cache_backfill",
                }
            ),
            raising=False,
        )

        client = TestClient(app)
        response = client.get(f"/api/v1/debates/{session_id}/report")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["source"] == "database_generated"
        assert data["structured_report"]["summary"] == "Resumen regenerado"

    def test_report_not_found(self):
        client = TestClient(app)
        response = client.get("/api/v1/debates/nonexistent/report")
        assert response.status_code == 404


class TestDebateContinuePauseResume:
    """Pruebas de endpoints continue/pause/resume"""

    def test_continue_debate_endpoint_exists(self):
        from backend.api.routes.debate import router

        continue_routes = [
            r for r in router.routes if hasattr(r, "path") and "/continue" in r.path
        ]
        assert len(continue_routes) >= 1, (
            "POST /debates/{session_id}/continue not found"
        )
        post_routes = [
            r for r in continue_routes if hasattr(r, "methods") and "POST" in r.methods
        ]
        assert len(post_routes) >= 1, "POST method not found for continue endpoint"

    def test_continue_debate_request_model(self):
        from backend.api.routes.debate import DebateContinueRequest

        req = DebateContinueRequest(
            max_additional_turns=2, continuation_prompt="Profundiza en el punto X"
        )
        assert req.max_additional_turns == 2
        assert req.continuation_prompt == "Profundiza en el punto X"
        assert req.agents is None

    def test_continue_debate_controller_method_exists(self):
        from backend.engine.sequential_debate_controller import (
            SequentialDebateController,
        )

        controller = SequentialDebateController()
        assert hasattr(controller, "continue_debate"), (
            "continue_debate method not found"
        )
        assert hasattr(controller, "_reconstruct_session_from_db"), (
            "_reconstruct_session_from_db method not found"
        )
        assert hasattr(controller, "_extract_agents_from_session"), (
            "_extract_agents_from_session method not found"
        )

    def test_pause_debate_endpoint_exists(self):
        from backend.api.routes.debate import router

        pause_routes = [
            r for r in router.routes if hasattr(r, "path") and "/pause" in r.path
        ]
        assert len(pause_routes) >= 1, "POST /debates/{session_id}/pause not found"
        post_routes = [
            r for r in pause_routes if hasattr(r, "methods") and "POST" in r.methods
        ]
        assert len(post_routes) >= 1, "POST method not found for pause endpoint"

    def test_resume_debate_endpoint_exists(self):
        from backend.api.routes.debate import router

        resume_routes = [
            r for r in router.routes if hasattr(r, "path") and "/resume" in r.path
        ]
        assert len(resume_routes) >= 1, "POST /debates/{session_id}/resume not found"
        post_routes = [
            r for r in resume_routes if hasattr(r, "methods") and "POST" in r.methods
        ]
        assert len(post_routes) >= 1, "POST method not found for resume endpoint"

    def test_pause_debate_request_model(self):
        from backend.api.routes.debate import DebatePauseRequest

        req = DebatePauseRequest(reason="Server maintenance")
        assert req.reason == "Server maintenance"

    def test_pause_resume_controller_methods_exist(self):
        from backend.engine.sequential_debate_controller import (
            SequentialDebateController,
        )

        controller = SequentialDebateController()
        assert hasattr(controller, "pause_debate"), "pause_debate method not found"
        assert hasattr(controller, "resume_debate"), "resume_debate method not found"

    def test_sequential_debate_model_has_pause_fields(self):
        from backend.database.models import SequentialDebate

        assert hasattr(SequentialDebate, "paused_at")
        assert hasattr(SequentialDebate, "pause_reason")


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
        from backend.api.routes.debate import export_debate_json

        assert export_debate_json is not None

    def test_export_markdown_content_type(self):
        from backend.api.routes.debate import export_debate_markdown

        assert export_debate_markdown is not None

    def test_export_pdf_content_type(self):
        from backend.api.routes.debate import export_debate_pdf

        assert export_debate_pdf is not None

    def test_export_json_includes_structured_metadata(self, monkeypatch):
        from backend.api.routes import debate as debate_routes
        from backend.engine.debate_models import (
            AgentRole,
            CruzamientoCritico,
            DebateAgent,
            DebateSession,
            DebateTurn,
            IteracionDebate,
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
            lambda session_id: session if session_id == session.id else None,
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
        assert data["iterations"][0]["consensus_points"] == [
            "La IA necesita supervision"
        ]
        assert data["iterations"][0]["dissent_areas"] == [
            "El grado de autonomia aceptable"
        ]
        assert data["iterations"][0]["cross_references"][0]["from_agent"] == "Critic"
