"""
Unit tests for logging configuration
"""

import logging
import shutil
import tempfile
from pathlib import Path

from backend.logging_config import (
    _APIFilter,
    _EngineFilter,
    setup_logging,
    shutdown_logging,
)


class TestLoggingConfig:
    """Pruebas de la configuracion de logging"""

    def test_logging_config_imports(self):
        assert callable(setup_logging)
        assert _EngineFilter is not None
        assert _APIFilter is not None

    def test_logging_config_creates_files(self):
        tmpdir = tempfile.mkdtemp()
        try:
            setup_logging(
                log_level="DEBUG",
                log_dir=Path(tmpdir),
                console=True,
                file_output=True,
            )
            log_file = Path(tmpdir) / "synapse.log"
            error_file = Path(tmpdir) / "synapse_error.log"
            engine_file = Path(tmpdir) / "synapse_engine.log"
            api_file = Path(tmpdir) / "synapse_api.log"
            assert log_file.exists()
            assert error_file.exists()
            assert engine_file.exists()
            assert api_file.exists()
        finally:
            shutdown_logging()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_engine_filter(self):
        f = _EngineFilter()
        record_engine = logging.LogRecord("backend.engine.sequential_debate_controller", 20, "", 0, "", (), None)
        record_other = logging.LogRecord("backend.config", 20, "", 0, "", (), None)
        assert f.filter(record_engine) is True
        assert f.filter(record_other) is False

    def test_api_filter(self):
        f = _APIFilter()
        record_api = logging.LogRecord("backend.api.routes.debate", 20, "", 0, "", (), None)
        record_other = logging.LogRecord("backend.engine.tribunal", 20, "", 0, "", (), None)
        assert f.filter(record_api) is True
        assert f.filter(record_other) is False
