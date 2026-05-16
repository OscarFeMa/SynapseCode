"""
Unit tests for semantic cache
"""
import numpy as np
from backend.caching.semantic_cache import SemanticCacheService


class TestSemanticCache:
    """Pruebas del sistema de cache semantica"""

    def test_cache_module_imports(self):
        assert SemanticCacheService is not None

    def test_cache_build_key(self):
        cache = SemanticCacheService()
        key = cache._generate_cache_key("test prompt", "llama3.2:latest", "ollama", 0.7)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_cache_similarity_threshold(self):
        cache = SemanticCacheService()
        assert hasattr(cache, "_similarity_threshold")
        assert 0.0 <= cache._similarity_threshold <= 1.0

    def test_cache_ttl_configurable(self):
        cache = SemanticCacheService()
        assert hasattr(cache, "_cache_ttl_hours")
        assert cache._cache_ttl_hours > 0

    def test_cache_cosine_similarity(self):
        cache = SemanticCacheService()
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])
        sim = cache._cosine_similarity(v1, v2)
        assert abs(sim - 1.0) < 0.001

    def test_cache_cosine_similarity_orthogonal(self):
        cache = SemanticCacheService()
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])
        sim = cache._cosine_similarity(v1, v2)
        assert abs(sim) < 0.001
