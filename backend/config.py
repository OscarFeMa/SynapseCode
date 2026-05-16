"""
Synapse Council v2.0 - Configuration
Pydantic Settings para validación de variables de entorno
"""
from pydantic import Field, field_validator, model_validator
from typing import List, Optional, Union
from functools import lru_cache
import socket
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada del sistema"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # ─── Rol del Nodo ─────────────────────────────────────────
    NODE_ROLE: str = Field(default="MASTER", pattern="^(MASTER|WORKER)$")
    WORKER_HOST: Optional[str] = None  # IP dinámica - se resuelve via hostname
    WORKER_HOSTNAME: str = "makederpc"  # Hostname del Worker para resolución DNS
    WORKER_OLLAMA_PORT: int = 11434
    WORKER_LM_STUDIO_PORT: int = 1234
    WORKER_JAN_PORT: int = 1337
    
    # ─── P2P Discovery (UDP) ──────────────────────────────────
    DISCOVERY_PORT: int = 54321
    DISCOVERY_INTERVAL: int = 5
    
    # ─── Heartbeat (basado en Pensamiento Coral) ─────────────
    HEARTBEAT_INTERVAL: int = 5
    HEARTBEAT_TIMEOUT: int = 15
    TCP_COMMAND_PORT: int = 54322
    
    # ─── Base de Datos ────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/synapse.db"
    
    # ─── Ollama ───────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT_SECONDS: int = 600
    OLLAMA_MAX_RETRIES: int = 2
    OLLAMA_KEEP_ALIVE: int = 0
    OLLAMA_PRELOAD_KEEP_ALIVE: int = 120
    
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
    OPENROUTER_ENABLED: bool = True
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api"
    OPENROUTER_TIMEOUT_SECONDS: int = 90
    OPENROUTER_MAX_RETRIES: int = 2
    OPENROUTER_HTTP_REFERER: str = "http://localhost:3000"
    OPENROUTER_APP_NAME: str = "SynapseCouncil"

    # ─── Google Gemini ────────────────────────────────────────
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_ENABLED: bool = True

    # ─── Groq ─────────────────────────────────────────────────
    GROQ_API_KEY: Optional[str] = None
    GROQ_ENABLED: bool = True

    # ─── DeepSeek ─────────────────────────────────────────────
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_ENABLED: bool = True
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    
    # ─── Web Agent (Playwright) ───────────────────────────────
    WEB_AGENT_ENABLED: bool = True
    WEB_AGENT_BROWSER: str = "chromium"  # "chromium" | "chrome" (usa Chrome del sistema con sesiones guardadas)
    WEB_AGENT_HEADLESS: bool = True
    WEB_AGENT_TIMEOUT_SECONDS: int = 120
    WEB_AGENT_SITES: str = "chat.openai.com,claude.ai,gemini.google.com,chat.deepseek.com,perplexity.ai,grok.com,chat.mistral.ai,meta.ai,huggingface.co/chat,you.com"
    WEB_AGENT_SESSION_DIR: str = "./data/browser_sessions"
    WEB_AGENT_CHROME_PATH: str = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    WEB_AGENT_CHROME_PROFILE: str = ""  # Vacío = usa perfil por defecto del usuario

    # ─── HuggingFace Inference API ───────────────────────────
    HF_TOKEN: Optional[str] = None
    HF_ENABLED: bool = True
    
    # ─── RDP Manager (Wake-on-RDP para Worker) ──────────────────
    RDP_ENABLED: bool = True
    RDP_WORKER_HOSTNAME: str = "makederpc"
    RDP_WORKER_USERNAME: str = "MAKEDER\\maked"
    RDP_WORKER_PASSWORD: str = ""  # DEBE configurarse en .env → RDP_WORKER_PASSWORD=...
    RDP_RATE_LIMIT_SECONDS: int = 60  # Mínimo tiempo entre wakes
    
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
    
    # ─── Feature Flags (Mejoras v2.1) ─────────────────────────
    INTERVENTION_TAXONOMY_ENABLED: bool = True
    QUALITY_MONITOR_ENABLED: bool = True
    HYBRID_MEMORY_V2_ENABLED: bool = True
    
    # ─── Semantic Cache ────────────────────────────────────────
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_TTL_HOURS: int = 24
    SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = 0.85
    
    # ─── Servidor ─────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:5177,http://localhost:5178,http://localhost:5179,http://localhost:5180"
    LOG_LEVEL: str = "INFO"
    RELOAD: bool = False

    # ─── Admin API ────────────────────────────────────────────
    ADMIN_API_TOKEN: Optional[str] = None
    ADMIN_API_LOCALHOST_ONLY: bool = True
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        if isinstance(v, list):
            return v
        return [origin.strip() for origin in v.split(",")]

    @field_validator("SUPABASE_URL", "SUPABASE_ANON_KEY", mode="before")
    @classmethod
    def normalize_placeholder_supabase_values(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if "CHANGEME" in value:
            return None
        return value

    @model_validator(mode="after")
    def disable_supabase_when_credentials_missing(self):
        if not self.SUPABASE_URL or not self.SUPABASE_ANON_KEY:
            self.SUPABASE_ENABLED = False
        return self
    
    @property
    def is_master(self) -> bool:
        return self.NODE_ROLE == "MASTER"
    
    @property
    def web_agent_sites_list(self) -> List[str]:
        return [site.strip() for site in self.WEB_AGENT_SITES.split(",")]
    
    def resolve_worker_ip(self) -> Optional[str]:
        """Resuelve la IP del Worker via DNS usando WORKER_HOSTNAME"""
        try:
            ip = socket.gethostbyname(self.WORKER_HOSTNAME)
            return ip
        except socket.gaierror:
            return None
    
    def get_worker_host(self) -> Optional[str]:
        """Obtiene la IP del Worker: usa WORKER_HOST si está seteada, sino resuelve dinámicamente"""
        if self.WORKER_HOST:
            return self.WORKER_HOST
        # Resolver dinámicamente via hostname
        resolved = self.resolve_worker_ip()
        if resolved:
            self.WORKER_HOST = resolved  # Cachear para esta sesión
        return resolved
    
    @property
    def worker_ollama_url(self) -> str:
        if self.is_master:
            host = self.get_worker_host()
            if host:
                return f"http://{host}:{self.WORKER_OLLAMA_PORT}"
        return self.OLLAMA_BASE_URL
    
    @property
    def worker_lm_studio_url(self) -> str:
        if self.is_master:
            host = self.get_worker_host()
            if host:
                return f"http://{host}:{self.WORKER_LM_STUDIO_PORT}"
        return self.LM_STUDIO_BASE_URL
    
    @property
    def worker_jan_url(self) -> str:
        if self.is_master:
            host = self.get_worker_host()
            if host:
                return f"http://{host}:{self.WORKER_JAN_PORT}"
        return self.JAN_BASE_URL
    
    def update_worker_host(self, host: str):
        """Actualiza la IP del Worker dinámicamente en tiempo de ejecución"""
        self.WORKER_HOST = host
    
    def clear_worker_host_cache(self):
        """Limpia la cache de IP del Worker para forzar re-resolución DNS"""
        self.WORKER_HOST = None


@lru_cache()
def get_settings() -> Settings:
    """Obtiene configuración cacheada (singleton)"""
    return Settings()

# Instancia global para import directo
settings = get_settings()
