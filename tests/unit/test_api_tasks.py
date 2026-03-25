"""Tests for task API routes — Supabase-based."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from agent_fleet.api.deps import get_current_user
from agent_fleet.api.routes.tasks import _get_repo
from agent_fleet.main import create_app

TEST_USER = {"id": "user-123", "email": "test@example.com"}


@pytest.fixture
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(mock_repo: MagicMock) -> TestClient:
    app = create_app()

    async def _fake_user() -> dict:
        return TEST_USER

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    return TestClient(app)


class TestSubmitTask:
    def test_submit_missing_repo_returns_422(self, client: TestClient) -> None:
        """POST /api/v1/tasks without repo field returns 422."""
        response = client.post(
            "/api/v1/tasks",
            json={"description": "Fix bug", "workflow_id": "wf-1"},
        )
        assert response.status_code == 422

    def test_submit_missing_description_returns_422(self, client: TestClient) -> None:
        """POST /api/v1/tasks without description field returns 422."""
        response = client.post(
            "/api/v1/tasks",
            json={"repo": "/tmp/repo", "workflow_id": "wf-1"},
        )
        assert response.status_code == 422

    def test_submit_missing_workflow_id_returns_422(self, client: TestClient) -> None:
        """POST /api/v1/tasks without workflow_id field returns 422."""
        response = client.post(
            "/api/v1/tasks",
            json={"repo": "/tmp/repo", "description": "Fix bug"},
        )
        assert response.status_code == 422

    def test_submit_creates_task(self, client: TestClient, mock_repo: MagicMock) -> None:
        """POST /api/v1/tasks creates a queued task."""
        mock_repo.create.return_value = {
            "id": "task-abc123",
            "repo": "/tmp/repo",
            "description": "Fix bug",
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

        response = client.post(
            "/api/v1/tasks",
            json={"repo": "/tmp/repo", "description": "Fix bug", "workflow_id": "wf-1"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"
        mock_repo.create.assert_called_once()


class TestListTasks:
    def test_list_empty_returns_empty_list(self, client: TestClient, mock_repo: MagicMock) -> None:
        """GET /api/v1/tasks returns empty list when no tasks exist."""
        mock_repo.list_by_user.return_value = []

        response = client.get("/api/v1/tasks")
        assert response.status_code == 200
        assert response.json() == {"tasks": []}

    def test_list_returns_user_tasks(self, client: TestClient, mock_repo: MagicMock) -> None:
        """GET /api/v1/tasks returns user's tasks."""
        mock_repo.list_by_user.return_value = [
            {
                "id": "task-1",
                "repo": "/tmp/repo",
                "description": "Task 1",
                "status": "completed",
                "workflow_name": "default",
                "current_stage": None,
                "completed_stages": ["plan"],
                "total_tokens": 500,
                "total_cost_usd": 0.01,
                "pr_url": None,
                "error_message": None,
                "created_at": "2026-03-23T00:00:00Z",
                "updated_at": "2026-03-23T00:00:00Z",
            }
        ]

        response = client.get("/api/v1/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1


class TestGetTask:
    def test_get_returns_task(self, client: TestClient, mock_repo: MagicMock) -> None:
        """GET /api/v1/tasks/{id} returns task details."""
        mock_repo.get.return_value = {
            "id": "task-1",
            "user_id": "user-123",
            "repo": "/tmp/repo",
            "description": "Task 1",
            "status": "running",
            "workflow_name": "default",
            "current_stage": "plan",
            "completed_stages": [],
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "pr_url": None,
            "error_message": None,
            "created_at": "2026-03-23T00:00:00Z",
            "updated_at": "2026-03-23T00:00:00Z",
        }

        response = client.get("/api/v1/tasks/task-1")
        assert response.status_code == 200

    def test_get_returns_404_for_missing(self, client: TestClient, mock_repo: MagicMock) -> None:
        """GET /api/v1/tasks/{id} returns 404 if not found."""
        mock_repo.get.return_value = None
        response = client.get("/api/v1/tasks/nonexistent")
        assert response.status_code == 404

    def test_get_returns_404_for_other_user(self, client: TestClient, mock_repo: MagicMock) -> None:
        """GET /api/v1/tasks/{id} returns 404 if task belongs to different user."""
        mock_repo.get.return_value = {
            "id": "task-1",
            "user_id": "other-user",
            "repo": "/tmp/repo",
            "description": "Not yours",
            "status": "running",
        }
        response = client.get("/api/v1/tasks/task-1")
        assert response.status_code == 404


class TestCancelTask:
    def test_cancel_sets_cancelled(self, client: TestClient, mock_repo: MagicMock) -> None:
        """DELETE /api/v1/tasks/{id}/cancel sets status to cancelled."""
        mock_repo.get.return_value = {
            "id": "task-1",
            "user_id": "user-123",
            "status": "running",
        }

        response = client.delete("/api/v1/tasks/task-1/cancel")
        assert response.status_code == 200
        mock_repo.update_status.assert_called_once_with("task-1", "cancelled")

    def test_cancel_rejects_completed_task(self, client: TestClient, mock_repo: MagicMock) -> None:
        """DELETE /api/v1/tasks/{id}/cancel returns 400 if task already completed."""
        mock_repo.get.return_value = {
            "id": "task-1",
            "user_id": "user-123",
            "status": "completed",
        }

        response = client.delete("/api/v1/tasks/task-1/cancel")
        assert response.status_code == 400

    def test_cancel_already_cancelled_returns_400(
        self, client: TestClient, mock_repo: MagicMock,
    ) -> None:
        """DELETE /api/v1/tasks/{id}/cancel returns 400 if task is already cancelled."""
        mock_repo.get.return_value = {
            "id": "task-1",
            "user_id": "user-123",
            "status": "cancelled",
        }

        response = client.delete("/api/v1/tasks/task-1/cancel")
        assert response.status_code == 400

    def test_cancel_wrong_user_returns_404(self, client: TestClient, mock_repo: MagicMock) -> None:
        """DELETE /api/v1/tasks/{id}/cancel returns 404 if task belongs to different user."""
        mock_repo.get.return_value = {
            "id": "task-1",
            "user_id": "other-user-456",
            "status": "running",
        }

        response = client.delete("/api/v1/tasks/task-1/cancel")
        assert response.status_code == 404
