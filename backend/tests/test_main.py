"""Basic tests for NeuroSeek backend."""
import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint returns basic info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["name"] == "NeuroSeek AI"


def test_health_endpoint(client: TestClient):
    """Test health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_health_ready_endpoint(client: TestClient):
    """Test health ready endpoint."""
    response = client.get("/api/v1/health/ready")
    # May return 503 if dependencies not ready, but should not 404
    assert response.status_code in [200, 503]


def test_openapi_docs(client: TestClient):
    """Test OpenAPI docs accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_openapi_json(client: TestClient):
    """Test OpenAPI JSON accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data