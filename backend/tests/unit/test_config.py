"""
Unit tests for configuration and settings
"""
from backend.config import get_settings


class TestConfig:
    """Verifica configuraciones basicas"""

    def test_env_vars(self):
        s = get_settings()
        assert "CHANGEME" not in (s.SUPABASE_URL or ""), "SUPABASE_URL contiene CHANGEME"
        assert "CHANGEME" not in (s.SUPABASE_ANON_KEY or ""), "SUPABASE_ANON_KEY contiene CHANGEME"

    def test_worker_urls(self):
        s = get_settings()
        if s.is_master:
            host = s.get_worker_host()
            assert host is not None, "Worker host no resuelto"
            assert s.worker_ollama_url.startswith("http://")
            assert s.worker_lm_studio_url.startswith("http://")


class TestConfigSettings:
    """Pruebas de la configuracion de la aplicacion"""

    def test_settings_node_role(self):
        s = get_settings()
        assert s.NODE_ROLE in ("MASTER", "WORKER")

    def test_settings_is_master(self):
        s = get_settings()
        assert isinstance(s.is_master, bool)

    def test_settings_get_worker_host(self):
        s = get_settings()
        if s.is_master:
            host = s.get_worker_host()
            assert host is not None

    def test_settings_port(self):
        s = get_settings()
        assert s.PORT == 8000

    def test_settings_api_keys_not_placeholder(self):
        s = get_settings()
        if s.GROQ_API_KEY:
            assert "CHANGEME" not in s.GROQ_API_KEY
        if s.GEMINI_API_KEY:
            assert "CHANGEME" not in s.GEMINI_API_KEY
        if s.OPENROUTER_API_KEY:
            assert "CHANGEME" not in s.OPENROUTER_API_KEY

    def test_settings_supabase_disabled_gracefully(self):
        s = get_settings()
        if not s.SUPABASE_URL or "CHANGEME" in (s.SUPABASE_URL or ""):
            assert s.SUPABASE_ENABLED is False or s.SUPABASE_URL is None

    def test_model_timeout_default_ollama(self):
        s = get_settings()
        timeout = s.get_model_timeout("llama3.2:latest", "ollama")
        assert timeout == s.OLLAMA_TIMEOUT_SECONDS

    def test_model_timeout_specific_70b(self):
        s = get_settings()
        timeout = s.get_model_timeout("llama3.1:70b", "ollama")
        assert timeout == 300

    def test_model_timeout_specific_405b(self):
        s = get_settings()
        timeout = s.get_model_timeout("llama3.1:405b", "ollama")
        assert timeout == 600

    def test_model_timeout_pattern_match(self):
        s = get_settings()
        timeout = s.get_model_timeout("deepseek-r1:70b-instruct", "ollama")
        assert timeout == 600

    def test_model_timeout_cloud_default(self):
        s = get_settings()
        timeout = s.get_model_timeout("gpt-4o", "openrouter")
        assert timeout == s.OPENROUTER_TIMEOUT_SECONDS

    def test_model_timeout_custom_default(self):
        s = get_settings()
        timeout = s.get_model_timeout("unknown-model", "ollama", default=120)
        assert timeout == 120

    def test_logging_config_settings_exist(self):
        s = get_settings()
        assert hasattr(s, "LOG_LEVEL")
        assert hasattr(s, "LOG_DIR")
        assert hasattr(s, "LOG_MAX_BYTES")
        assert hasattr(s, "LOG_BACKUP_COUNT")
        assert hasattr(s, "LOG_TO_FILE")
        assert s.LOG_LEVEL in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        assert s.LOG_MAX_BYTES > 0
        assert s.LOG_BACKUP_COUNT > 0
