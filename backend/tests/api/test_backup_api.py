"""
API tests for backup endpoints
"""

from fastapi.testclient import TestClient

from backend.main import app


class TestBackupEndpoints:
    """Pruebas de endpoints de backup"""

    def test_backup_status_endpoint(self, monkeypatch):
        from backend.api.routes import system as system_routes

        monkeypatch.setattr(system_routes.settings, "ADMIN_API_LOCALHOST_ONLY", False)
        client = TestClient(app)
        response = client.get("/api/v1/system/backup/status")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "supabase_configured" in data
        assert "database_path" in data
        assert "database_exists" in data
        assert "bucket" in data

    def test_backup_create_endpoint(self, monkeypatch):
        from backend.api.routes import system as system_routes

        monkeypatch.setattr(system_routes.settings, "ADMIN_API_LOCALHOST_ONLY", False)
        client = TestClient(app)
        response = client.post("/api/v1/system/backup/create")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_backup_list_endpoint(self, monkeypatch):
        from backend.api.routes import system as system_routes

        monkeypatch.setattr(system_routes.settings, "ADMIN_API_LOCALHOST_ONLY", False)
        client = TestClient(app)
        response = client.get("/api/v1/system/backup/list")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "backups" in data
