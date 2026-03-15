"""Tests for webhook handlers and GitHub integration."""
from fastapi.testclient import TestClient

from agent_fleet.integrations.github import issue_to_task
from agent_fleet.main import create_app


class TestGitHubWebhook:
    def test_accepts_issue_opened_event(self) -> None:
        app = create_app(database_url="sqlite:///:memory:")
        # Wire webhook router
        from agent_fleet.api.routes import webhooks
        app.include_router(webhooks.router)

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/webhooks/github",
                json={
                    "action": "opened",
                    "issue": {
                        "number": 42,
                        "title": "Add multiply function",
                        "body": "Please add multiply(a, b)",
                        "labels": [],
                    },
                    "repository": {
                        "full_name": "org/repo",
                        "clone_url": "https://github.com/org/repo.git",
                    },
                },
                headers={"X-GitHub-Event": "issues"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "accepted"

    def test_ignores_non_issue_events(self) -> None:
        app = create_app(database_url="sqlite:///:memory:")
        from agent_fleet.api.routes import webhooks
        app.include_router(webhooks.router)

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/webhooks/github",
                json={"action": "created"},
                headers={"X-GitHub-Event": "push"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "ignored"


class TestIssueToTask:
    def test_converts_issue_to_task(self) -> None:
        payload = {
            "issue": {
                "number": 7,
                "title": "Add multiply",
                "body": "Add multiply(a, b) function",
                "labels": [],
            },
            "repository": {
                "full_name": "org/repo",
                "clone_url": "https://github.com/org/repo.git",
            },
        }
        result = issue_to_task(payload)
        assert "multiply" in result["description"]
        assert result["issue_number"] == "7"
        assert result["workflow"] == "default"

    def test_detects_workflow_from_labels(self) -> None:
        payload = {
            "issue": {
                "number": 8,
                "title": "Fix bug",
                "body": "",
                "labels": [{"name": "backend-only"}],
            },
            "repository": {"full_name": "org/repo", "clone_url": ""},
        }
        result = issue_to_task(payload)
        assert result["workflow"] == "two-stage"
