"""Tests for FastAPI app factory and health endpoint."""

from fastapi.testclient import TestClient

from agent_fleet.api.schemas import HealthResponse
from agent_fleet.main import create_app


class TestAppFactory:
    def test_create_app_returns_fastapi(self) -> None:
        app = create_app()
        assert app is not None
        assert app.title == "Agent Fleet"

    def test_health_endpoint(self) -> None:
        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["version"] == "0.1.0"


class TestHealthSchema:
    def test_health_response_defaults(self) -> None:
        resp = HealthResponse(version="0.1.0")
        assert resp.status == "ok"
