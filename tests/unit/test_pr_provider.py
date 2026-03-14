"""Tests for PR provider — GitHub, GitLab, local summary."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_fleet.workspace.pr import (
    GitHubPRProvider,
    GitLabPRProvider,
    LocalSummaryProvider,
    detect_provider,
    generate_pr_body,
)


class TestLocalSummaryProvider:
    def test_writes_summary_file(self, tmp_path: Path) -> None:
        provider = LocalSummaryProvider()
        result = provider.create_pr(
            repo_path=tmp_path,
            branch="fleet/task-001",
            title="Add multiply",
            body="## Summary\nAdded multiply function",
        )
        assert result is None  # Local provider returns None (no URL)
        summary_path = tmp_path / "fleet-summary.md"
        assert summary_path.exists()
        content = summary_path.read_text()
        assert "Add multiply" in content
        assert "Summary" in content


class TestGitHubPRProvider:
    @patch("agent_fleet.workspace.pr.shutil.which")
    @patch("agent_fleet.workspace.pr.subprocess.run")
    def test_creates_pr_via_gh(
        self, mock_run: MagicMock, mock_which: MagicMock
    ) -> None:
        mock_which.return_value = "/usr/local/bin/gh"
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/org/repo/pull/42\n"
        )
        provider = GitHubPRProvider()
        url = provider.create_pr(
            repo_path=Path("/repo"),
            branch="fleet/task-001",
            title="Add multiply",
            body="Summary here",
        )
        assert url == "https://github.com/org/repo/pull/42"
        mock_run.assert_called_once()

    @patch("agent_fleet.workspace.pr.subprocess.run")
    def test_returns_none_on_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="error")
        provider = GitHubPRProvider()
        url = provider.create_pr(
            repo_path=Path("/repo"),
            branch="fleet/task-001",
            title="Test",
            body="Body",
        )
        assert url is None


class TestGitLabPRProvider:
    @patch("agent_fleet.workspace.pr.subprocess.run")
    def test_creates_mr_via_glab(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://gitlab.com/org/repo/-/merge_requests/7\n"
        )
        provider = GitLabPRProvider()
        url = provider.create_pr(
            repo_path=Path("/repo"),
            branch="fleet/task-001",
            title="Add multiply",
            body="Summary",
        )
        assert url == "https://gitlab.com/org/repo/-/merge_requests/7"


class TestDetectProvider:
    @patch("agent_fleet.workspace.pr.shutil.which")
    def test_detects_github(self, mock_which: MagicMock) -> None:
        mock_which.side_effect = lambda cmd: "/usr/local/bin/gh" if cmd == "gh" else None
        provider = detect_provider(Path("/repo"))
        assert isinstance(provider, GitHubPRProvider)

    @patch("agent_fleet.workspace.pr.shutil.which")
    def test_detects_gitlab(self, mock_which: MagicMock) -> None:
        mock_which.side_effect = lambda cmd: "/usr/local/bin/glab" if cmd == "glab" else None
        provider = detect_provider(Path("/repo"))
        assert isinstance(provider, GitLabPRProvider)

    @patch("agent_fleet.workspace.pr.shutil.which")
    def test_falls_back_to_local(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        provider = detect_provider(Path("/repo"))
        assert isinstance(provider, LocalSummaryProvider)


class TestGeneratePRBody:
    def test_generates_markdown_from_stage_outputs(self) -> None:
        stage_outputs = {
            "plan": {"success": True, "output": "Add multiply function"},
            "backend": {
                "success": True,
                "output": "Implemented multiply",
                "files_changed": ["src/calculator.py"],
                "tokens_used": 500,
            },
            "review": {
                "success": True,
                "output": '{"score": 90, "reasoning": "Looks good"}',
            },
        }
        body = generate_pr_body(
            description="Add multiply",
            workflow_name="default",
            total_tokens=1500,
            stage_outputs=stage_outputs,
        )
        assert "Add multiply" in body
        assert "Plan" in body or "plan" in body
        assert "Backend" in body or "backend" in body
        assert "1500" in body or "1,500" in body
