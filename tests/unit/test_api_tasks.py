"""Tests for task CRUD routes."""

import pytest
from fastapi.testclient import TestClient

from agent_fleet.main import create_app


@pytest.fixture
def client() -> TestClient:  # type: ignore[misc]
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestSubmitTask:
    def test_submit_returns_201(self, client: TestClient) -> None:
        resp = client.post("/api/v1/tasks", json={
            "repo": "/path/to/repo",
            "description": "Implement feature X",
            "workflow": "default",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "queued"

    def test_submit_generates_unique_ids(self, client: TestClient) -> None:
        r1 = client.post("/api/v1/tasks", json={
            "repo": "/r", "description": "A",
        })
        r2 = client.post("/api/v1/tasks", json={
            "repo": "/r", "description": "B",
        })
        assert r1.json()["task_id"] != r2.json()["task_id"]

    def test_submit_default_workflow(self, client: TestClient) -> None:
        resp = client.post("/api/v1/tasks", json={
            "repo": "/r", "description": "Test",
        })
        assert resp.json()["workflow"] == "default"

    def test_submit_missing_fields_returns_422(self, client: TestClient) -> None:
        resp = client.post("/api/v1/tasks", json={"repo": "/r"})
        assert resp.status_code == 422


class TestGetTask:
    def test_get_existing_task(self, client: TestClient) -> None:
        create = client.post("/api/v1/tasks", json={
            "repo": "/repo", "description": "Test",
        })
        task_id = create.json()["task_id"]
        resp = client.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["task_id"] == task_id
        assert resp.json()["description"] == "Test"

    def test_get_nonexistent_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/tasks/nonexistent")
        assert resp.status_code == 404


class TestListTasks:
    def test_list_returns_all_tasks(self, client: TestClient) -> None:
        client.post("/api/v1/tasks", json={"repo": "/r", "description": "A"})
        client.post("/api/v1/tasks", json={"repo": "/r", "description": "B"})
        resp = client.get("/api/v1/tasks")
        assert resp.status_code == 200
        assert len(resp.json()["tasks"]) >= 2

    def test_list_empty_returns_empty(self, client: TestClient) -> None:
        resp = client.get("/api/v1/tasks")
        assert resp.status_code == 200
        assert resp.json()["tasks"] == []
