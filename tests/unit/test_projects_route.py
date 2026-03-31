"""Tests for project API routes."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from agent_fleet.api.deps import get_current_user
from agent_fleet.api.routes.projects import _get_repo, _get_task_repo
from agent_fleet.main import create_app

TEST_USER = {"id": "user-123", "email": "test@example.com"}

PROJECT_ROW = {
    "id": "p1",
    "user_id": "user-123",
    "name": "My Project",
    "repo_path": "/tmp/repo",
    "languages": ["python"],
    "frameworks": [],
    "test_frameworks": [],
    "databases": [],
    "has_ci": False,
    "ci_platform": None,
    "has_docker": False,
    "estimated_loc": None,
    "created_at": "2026-03-29T00:00:00Z",
    "updated_at": "2026-03-29T00:00:00Z",
}


@pytest.fixture
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_task_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(mock_repo: MagicMock, mock_task_repo: MagicMock) -> TestClient:
    app = create_app()

    async def _fake_user() -> dict:
        return TEST_USER

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    app.dependency_overrides[_get_task_repo] = lambda: mock_task_repo
    return TestClient(app)


class TestListProjects:
    def test_returns_user_projects(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.list_by_user.return_value = [PROJECT_ROW]
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "My Project"

    def test_empty_list(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.list_by_user.return_value = []
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_scoped_to_user(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.list_by_user.return_value = []
        client.get("/api/v1/projects")
        mock_repo.list_by_user.assert_called_once_with("user-123")


class TestCreateProject:
    def test_creates_project(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.create.return_value = PROJECT_ROW
        resp = client.post(
            "/api/v1/projects",
            json={"name": "My Project", "repo_path": "/tmp/repo", "languages": ["python"]},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "My Project"

    def test_missing_name_returns_422(self, client: TestClient, mock_repo: MagicMock) -> None:
        resp = client.post("/api/v1/projects", json={"repo_path": "/tmp"})
        assert resp.status_code == 422

    def test_missing_repo_path_returns_422(self, client: TestClient, mock_repo: MagicMock) -> None:
        resp = client.post("/api/v1/projects", json={"name": "Test"})
        assert resp.status_code == 422


class TestGetProject:
    def test_returns_project_with_task_count(
        self, client: TestClient, mock_repo: MagicMock, mock_task_repo: MagicMock
    ) -> None:
        mock_repo.get.return_value = PROJECT_ROW
        mock_task_repo.count_by_project.return_value = 5
        resp = client.get("/api/v1/projects/p1")
        assert resp.status_code == 200
        assert resp.json()["task_count"] == 5

    def test_404_for_missing(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.get.return_value = None
        resp = client.get("/api/v1/projects/nonexistent")
        assert resp.status_code == 404

    def test_404_for_other_user(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.get.return_value = {**PROJECT_ROW, "user_id": "other-user"}
        resp = client.get("/api/v1/projects/p1")
        assert resp.status_code == 404


class TestUpdateProject:
    def test_updates_project(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.get.return_value = PROJECT_ROW
        mock_repo.update.return_value = {**PROJECT_ROW, "name": "Updated"}
        resp = client.put("/api/v1/projects/p1", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_empty_update_returns_400(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.get.return_value = PROJECT_ROW
        resp = client.put("/api/v1/projects/p1", json={})
        assert resp.status_code == 400

    def test_404_for_other_user(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.get.return_value = {**PROJECT_ROW, "user_id": "other-user"}
        resp = client.put("/api/v1/projects/p1", json={"name": "X"})
        assert resp.status_code == 404


class TestDeleteProject:
    def test_deletes_project(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.get.return_value = PROJECT_ROW
        resp = client.delete("/api/v1/projects/p1")
        assert resp.status_code == 204
        mock_repo.delete.assert_called_once_with("p1")

    def test_404_for_other_user(self, client: TestClient, mock_repo: MagicMock) -> None:
        mock_repo.get.return_value = {**PROJECT_ROW, "user_id": "other-user"}
        resp = client.delete("/api/v1/projects/p1")
        assert resp.status_code == 404
