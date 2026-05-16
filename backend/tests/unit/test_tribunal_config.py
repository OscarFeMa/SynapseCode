"""
Unit tests for tribunal configuration
"""

from backend.config import get_settings
from backend.engine.tribunal_config import build_tribunal_config


class TestTribunalConfig:
    """Pruebas de la configuracion del Tribunal"""

    def test_tribunal_config_build(self):
        config = build_tribunal_config(get_settings())
        assert "evidence" in config
        assert "risk" in config
        assert "alignment" in config

    def test_tribunal_config_has_fallback_chains(self):
        config = build_tribunal_config(get_settings())
        for role_name, role_config in config.items():
            assert role_config.chain is not None, f"{role_name} has no fallback chain"
            assert len(role_config.chain) >= 1, f"{role_name} chain is empty"

    def test_tribunal_config_env_override(self):
        settings = get_settings()
        config = build_tribunal_config(settings)
        assert config["evidence"].primary.node in ("LOCAL", "CLOUD")
        assert config["risk"].primary.node in ("LOCAL", "CLOUD")
        assert config["alignment"].primary.node in ("LOCAL", "CLOUD")

    def test_tribunal_config_module(self):
        config = build_tribunal_config(get_settings())
        assert set(config.keys()) == {"evidence", "risk", "alignment"}
        assert config["evidence"].primary.slot == "magistrate_evidence"
        assert config["risk"].primary.slot == "magistrate_risk"
        assert config["alignment"].primary.node == "LOCAL"
        assert all(role_config.chain for role_config in config.values())
