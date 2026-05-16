"""
API tests for cache endpoints
"""

from fastapi.testclient import TestClient

from backend.main import app


class TestCacheEndpoints:
    """Pruebas de endpoints de cache"""

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
