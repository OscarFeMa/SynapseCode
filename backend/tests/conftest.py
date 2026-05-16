"""
SynapseCode - Shared test fixtures and configuration
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Provide a TestClient instance for API tests."""
    return TestClient(app)


@pytest.fixture
def app_instance():
    """Provide the FastAPI app instance."""
    return app
