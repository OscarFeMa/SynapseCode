"""
SynapseCode - Shared test fixtures and configuration
"""

import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
)

from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """Provide a TestClient instance for API tests."""
    return TestClient(app)


@pytest.fixture
def app_instance():
    """Provide the FastAPI app instance."""
    return app
