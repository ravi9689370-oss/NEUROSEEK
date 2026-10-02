"""Pytest configuration for NeuroSeek backend tests."""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["OLLAMA_HOST"] = "http://localhost:11434"
os.environ["AUTH_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["MINIO_ENDPOINT"] = "localhost:9000"
os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
os.environ["MINIO_SECRET_KEY"] = "minioadmin"

# Mock database and other external dependencies before importing app
sys.modules["app.core.database"] = MagicMock()
sys.modules["app.services.inference.engine"] = MagicMock()
sys.modules["app.services.routing.router"] = MagicMock()
sys.modules["app.services.routing.ensemble"] = MagicMock()
sys.modules["app.services.training.scheduler"] = MagicMock()

# Now import the app
from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock external services for all tests."""
    with patch("app.core.database.init_db", new_callable=AsyncMock) as mock_init_db, \
         patch("app.core.database.close_db", new_callable=AsyncMock) as mock_close_db, \
         patch("app.services.inference.engine.get_inference_engine", new_callable=AsyncMock) as mock_get_engine, \
         patch("app.services.inference.engine.close_inference_engine", new_callable=AsyncMock) as mock_close_engine, \
         patch("app.services.routing.router.get_model_router", new_callable=AsyncMock) as mock_get_router, \
         patch("app.services.routing.ensemble.get_ensemble_manager", new_callable=AsyncMock) as mock_get_ensemble, \
         patch("app.services.training.scheduler.get_training_scheduler", new_callable=AsyncMock) as mock_get_scheduler:
        
        mock_scheduler = AsyncMock()
        mock_get_scheduler.return_value = mock_scheduler
        
        yield {
            "init_db": mock_init_db,
            "close_db": mock_close_db,
            "get_engine": mock_get_engine,
            "close_engine": mock_close_engine,
            "get_router": mock_get_router,
            "get_ensemble": mock_get_ensemble,
            "get_scheduler": mock_get_scheduler,
        }