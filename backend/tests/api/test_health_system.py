"""
API tests for health and system endpoints
"""

from fastapi.testclient import TestClient

from backend.main import app


class TestHealthEndpoints:
    """Pruebas de endpoints de health"""

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

    def test_root_endpoint(self):
        client = TestClient(app)
        response = client.get("/", headers={"Accept": "application/json"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "SynapseCode"
        assert "version" in data
        assert "node_role" in data


class TestSystemEndpoints:
    """Pruebas de endpoints del sistema"""

    def test_prometheus_metrics_endpoint_exposes_core_metrics(self):
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

    def test_tribunal_config_endpoint_returns_effective_roles(self, monkeypatch):
        from backend.api.routes import system as system_routes

        monkeypatch.setattr(system_routes.settings, "ADMIN_API_LOCALHOST_ONLY", False)
        client = TestClient(app)
        response = client.get("/api/v1/system/tribunal/config")
        assert response.status_code == 200
        data = response.json()
        assert data["maxIterations"] >= 1
        assert set(data["roles"].keys()) == {"evidence", "risk", "alignment"}
        assert data["roles"]["evidence"]["primary"]["slot"] == "magistrate_evidence"
        assert isinstance(data["roles"]["risk"]["fallbacks"], list)

    def test_system_analytics_endpoint_exists(self):
        client = TestClient(app)
        response = client.get("/api/v1/system/analytics")
        assert response.status_code in (200, 403)

    def test_reductio_analytics_endpoint_exists(self, monkeypatch):
        from backend.api.routes import system as system_routes

        monkeypatch.setattr(system_routes.settings, "ADMIN_API_LOCALHOST_ONLY", False)
        client = TestClient(app)
        response = client.get("/api/v1/system/reductio/analytics")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "totalProofs" in data["summary"]
        assert "avgConfidence" in data["summary"]
        assert "recentProofs" in data
