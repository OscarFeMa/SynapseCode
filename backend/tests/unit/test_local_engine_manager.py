"""
Unit tests for local engine manager
"""
from backend.engine.local_engine_manager import LocalEngineManager, EngineType


class TestLocalEngineManager:
    """Pruebas del gestor de motores locales"""

    def test_local_engine_manager_imports(self):
        assert LocalEngineManager is not None
        assert EngineType is not None

    def test_engine_type_enum(self):
        assert hasattr(EngineType, "OLLAMA")
        assert hasattr(EngineType, "LM_STUDIO")
        assert hasattr(EngineType, "JAN")

    def test_local_engine_manager_instance(self):
        manager = LocalEngineManager()
        assert hasattr(manager, "engines")
        assert hasattr(manager, "generate")

    def test_local_engine_manager_schedule_preload(self):
        manager = LocalEngineManager()
        assert hasattr(manager, "schedule_ollama_preload")
