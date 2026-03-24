"""Tests for API task submission triggering background worker."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from agent_fleet.api.deps import get_current_user
from agent_fleet.api.routes.tasks import _get_repo
from agent_fleet.main import create_app


class TestTaskSubmitWorker:
    def test_submit_returns_201_immediately(self) -> None:
        app = create_app()

        async def _fake_user() -> dict:
            return {"id": "user-123", "email": "test@example.com"}

        repo = MagicMock()
        repo.create.return_value = {
            "id": "task-abc",
            "repo": "/tmp/test",
            "description": "Test task",
            "status": "queued",
            "workflow_name": "default",
            "current_stage": None,
            "completed_stages": [],
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "pr_url": None,
            "error_message": None,
            "created_at": "2026-03-23T00:00:00Z",
            "updated_at": "2026-03-23T00:00:00Z",
        }

        app.dependency_overrides[get_current_user] = _fake_user
        app.dependency_overrides[_get_repo] = lambda: repo

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/tasks",
                json={"repo": "/tmp/test", "description": "Test task", "workflow_id": "wf-1"},
            )
            assert resp.status_code == 201
            assert resp.json()["status"] == "queued"
