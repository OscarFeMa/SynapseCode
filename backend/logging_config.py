"""
SynapseCode v2.7 - Logging Configuration
Rotating file handlers + console output + structured logging
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import structlog

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

_active_handlers = []


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    max_bytes: int = MAX_LOG_SIZE_BYTES,
    backup_count: int = BACKUP_COUNT,
    console: bool = True,
    file_output: bool = True,
) -> None:
    """
    Configura logging rotatorio con salida a consola y archivos.

    Archivos generados:
    - logs/synapse.log — Todos los logs
    - logs/synapse_engine.log — Solo motor de debate
    - logs/synapse_api.log — Solo peticiones HTTP/API
    - logs/synapse_error.log — Solo errores (ERROR+)

    Args:
        log_level: Nivel de logging global (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directorio para logs (default: backend/logs/)
        max_bytes: Tamaño maximo por archivo antes de rotar
        backup_count: Numero de archivos de backup a mantener
        console: Mostrar logs en consola
        file_output: Escribir logs a archivos
    """
    if log_dir is None:
        log_dir = LOGS_DIR

    log_level_num = getattr(logging, log_level.upper(), logging.INFO)

    # Handlers
    handlers = []

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level_num)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        handlers.append(console_handler)

    if file_output:
        # Log general (todos los logs)
        general_handler = RotatingFileHandler(
            log_dir / "synapse.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        general_handler.setLevel(log_level_num)
        general_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        handlers.append(general_handler)
        _active_handlers.append(general_handler)

        # Log de errores (solo ERROR y CRITICAL)
        error_handler = RotatingFileHandler(
            log_dir / "synapse_error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        handlers.append(error_handler)
        _active_handlers.append(error_handler)

        # Log del engine (debates, agentes, tribunal)
        engine_handler = RotatingFileHandler(
            log_dir / "synapse_engine.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        engine_handler.setLevel(log_level_num)
        engine_handler.addFilter(_EngineFilter())
        engine_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        handlers.append(engine_handler)
        _active_handlers.append(engine_handler)

        # Log de API (peticiones HTTP, middleware)
        api_handler = RotatingFileHandler(
            log_dir / "synapse_api.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        api_handler.setLevel(log_level_num)
        api_handler.addFilter(_APIFilter())
        api_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        handlers.append(api_handler)
        _active_handlers.append(api_handler)

    # Configurar logging estandar
    logging.basicConfig(
        level=log_level_num,
        handlers=handlers,
        force=True,
    )

    # Configurar structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if file_output
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


class _EngineFilter(logging.Filter):
    """Filtra logs relacionados con el motor de debate"""

    ENGINE_MODULES = {
        "backend.engine",
        "backend.engine.sequential_debate_controller",
        "backend.engine.tribunal",
        "backend.engine.convergence",
        "backend.engine.quality_monitor",
        "backend.engine.reputation_unified",
        "backend.engine.task_manager",
        "backend.engine.local_engine_manager",
        "backend.engine.reductio_absurdum",
        "backend.engine.intervention_taxonomy",
        "backend.engine.worker_launcher",
        "backend.engine.consensus_debate_controller",
        "backend.engine.ultra_debate_controller",
        "backend.engine.session_manager",
        "backend.engine.round_controller",
        "backend.engine.agent_orchestrator",
        "backend.engine.base_debate_controller",
        "backend.adapters",
        "backend.adapters.ollama",
        "backend.adapters.groq",
        "backend.adapters.gemini",
        "backend.adapters.openrouter",
        "backend.adapters.deepseek",
        "backend.adapters.lm_studio",
        "backend.adapters.web_agent",
        "backend.adapters.base",
        "backend.adapters.http_client_manager",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        return any(record.name.startswith(mod) for mod in self.ENGINE_MODULES)


class _APIFilter(logging.Filter):
    """Filtra logs relacionados con la API HTTP"""

    API_MODULES = {
        "backend.api",
        "backend.api.routes",
        "backend.api.middleware",
        "backend.api.websocket",
        "backend.main",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        return any(record.name.startswith(mod) for mod in self.API_MODULES)


def shutdown_logging() -> None:
    """Cierra todos los handlers de archivo activos (util para tests)."""
    for handler in _active_handlers:
        handler.close()
    _active_handlers.clear()
