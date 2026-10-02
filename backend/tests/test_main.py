"""Basic tests for NeuroSeek backend."""
import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns basic info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["name"] == "NeuroSeek AI"


def test_health_endpoint():
    """Test health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_health_ready_endpoint():
    """Test health ready endpoint."""
    response = client.get("/api/v1/health/ready")
    # May return 503 if dependencies not ready, but should not 404
    assert response.status_code in [200, 503]


def test_openapi_docs():
    """Test OpenAPI docs accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_openapi_json():
    """Test OpenAPI JSON accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data