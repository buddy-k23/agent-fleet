"""Tests for API task submission triggering background worker."""
from fastapi.testclient import TestClient

from agent_fleet.main import create_app


class TestTaskSubmitWorker:
    def test_submit_returns_201_immediately(self) -> None:
        app = create_app(database_url="sqlite:///:memory:")
        with TestClient(app) as client:
            resp = client.post("/api/v1/tasks", json={
                "repo": "/tmp/test", "description": "Test task",
            })
            assert resp.status_code == 201
            assert resp.json()["status"] == "queued"
