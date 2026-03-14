"""Tests for FastAPI app factory and health endpoint."""

from fastapi.testclient import TestClient

from agent_fleet.api.schemas import HealthResponse, TaskResponse, TaskSubmitRequest
from agent_fleet.main import create_app


class TestAppFactory:
    def test_create_app_returns_fastapi(self) -> None:
        app = create_app(database_url="sqlite:///:memory:")
        assert app is not None
        assert app.title == "Agent Fleet"

    def test_health_endpoint(self) -> None:
        app = create_app(database_url="sqlite:///:memory:")
        with TestClient(app) as client:
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["version"] == "0.1.0"


class TestSchemas:
    def test_task_submit_request_defaults(self) -> None:
        req = TaskSubmitRequest(repo="/repo", description="Test")
        assert req.workflow == "default"

    def test_task_submit_request_custom_workflow(self) -> None:
        req = TaskSubmitRequest(repo="/repo", description="Test", workflow="custom")
        assert req.workflow == "custom"

    def test_task_response_fields(self) -> None:
        resp = TaskResponse(
            task_id="t1", repo="/r", description="D", status="queued", workflow="default"
        )
        assert resp.task_id == "t1"
        assert resp.status == "queued"

    def test_health_response_defaults(self) -> None:
        resp = HealthResponse(version="0.1.0")
        assert resp.status == "ok"
