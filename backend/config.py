"""
Synapse Council v2.0 - Configuration
Pydantic Settings para validación de variables de entorno
"""
from functools import lru_cache
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Configuración centralizada del sistema"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # ─── Rol del Nodo ─────────────────────────────────────────
    NODE_ROLE: str = Field(default="MASTER", pattern="^(MASTER|WORKER)$")
    WORKER_HOST: Optional[str] = None
    WORKER_OLLAMA_PORT: int = 11434
    WORKER_LM_STUDIO_PORT: int = 1234
    WORKER_JAN_PORT: int = 1337
    
    # ─── P2P Discovery (UDP) ──────────────────────────────────
    DISCOVERY_PORT: int = 54321
    DISCOVERY_INTERVAL: int = 5
    
    # ─── Base de Datos ────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/synapse.db"
    
    # ─── Ollama ───────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT_SECONDS: int = 120
    OLLAMA_MAX_RETRIES: int = 2
    OLLAMA_KEEP_ALIVE: int = 0
    
    # ─── LM Studio ────────────────────────────────────────────
    LM_STUDIO_BASE_URL: str = "http://localhost:1234"
    LM_STUDIO_TIMEOUT_SECONDS: int = 120
    LM_STUDIO_MAX_RETRIES: int = 2
    LM_STUDIO_KEEP_ALIVE: int = 0
    
    # ─── Jan.ai ───────────────────────────────────────────────
    JAN_BASE_URL: str = "http://localhost:1337"
    JAN_TIMEOUT_SECONDS: int = 120
    JAN_MAX_RETRIES: int = 2
    JAN_KEEP_ALIVE: int = 0
    
    # ─── OpenRouter ───────────────────────────────────────────
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_TIMEOUT_SECONDS: int = 90
    OPENROUTER_MAX_RETRIES: int = 2
    OPENROUTER_HTTP_REFERER: str = "http://localhost:3000"
    OPENROUTER_APP_NAME: str = "SynapseCouncil"
    
    # ─── Web Agent (Playwright) ───────────────────────────────
    WEB_AGENT_ENABLED: bool = True
    WEB_AGENT_BROWSER: str = "chromium"
    WEB_AGENT_HEADLESS: bool = True
    WEB_AGENT_TIMEOUT_SECONDS: int = 120
    WEB_AGENT_SITES: str = "chat.openai.com,claude.ai,gemini.google.com"
    WEB_AGENT_SESSION_DIR: str = "./data/browser_sessions"
    
    # ─── Supabase ─────────────────────────────────────────────
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_ENABLED: bool = True
    SUPABASE_PROJECT: str = "memoria-oscar"
    
    # ─── Sistema de Reputación ────────────────────────────────
    AGENT_REPUTATION_ENABLED: bool = True
    REPUTATION_EMA_ALPHA: float = 0.3
    REPUTATION_MIN_DEBATES_FOR_WEIGHT: int = 3
    
    # ─── Motor ────────────────────────────────────────────────
    MAX_CONCURRENT_SESSIONS: int = 3
    DEFAULT_MAX_ROUNDS: int = 3
    DEFAULT_COST_LIMIT_USD: float = 1.00
    AUTO_ELEVATION_ENABLED: bool = True
    TRIBUNAL_MAX_ITERATIONS: int = 3
    
    # ─── Servidor ─────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173"
    LOG_LEVEL: str = "INFO"
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        if isinstance(v, list):
            return v
        return [origin.strip() for origin in v.split(",")]
    
    @property
    def is_master(self) -> bool:
        return self.NODE_ROLE == "MASTER"
    
    @property
    def web_agent_sites_list(self) -> List[str]:
        return [site.strip() for site in self.WEB_AGENT_SITES.split(",")]
    
    @property
    def worker_ollama_url(self) -> str:
        if self.is_master and self.WORKER_HOST:
            return f"http://{self.WORKER_HOST}:{self.WORKER_OLLAMA_PORT}"
        return self.OLLAMA_BASE_URL
    
    @property
    def worker_lm_studio_url(self) -> str:
        if self.is_master and self.WORKER_HOST:
            return f"http://{self.WORKER_HOST}:{self.WORKER_LM_STUDIO_PORT}"
        return self.LM_STUDIO_BASE_URL
    
    @property
    def worker_jan_url(self) -> str:
        if self.is_master and self.WORKER_HOST:
            return f"http://{self.WORKER_HOST}:{self.WORKER_JAN_PORT}"
        return self.JAN_BASE_URL
    
    def update_worker_host(self, host: str):
        """Actualiza la IP del Worker dinámicamente en tiempo de ejecución"""
        self.WORKER_HOST = host


@lru_cache()
def get_settings() -> Settings:
    """Obtiene configuración cacheada (singleton)"""
    return Settings()
