"""Test parallel stage execution — backend+frontend run concurrently."""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_fleet.core.orchestrator import FleetOrchestrator
from agent_fleet.core.state import FleetState
from agent_fleet.models.provider import LLMResponse

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
TEST_REPO_SRC = Path(__file__).parent.parent / "fixtures" / "test-repo"


@pytest.fixture
def test_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "test-repo"
    shutil.copytree(TEST_REPO_SRC, repo)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t.com"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "T"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "branch", "fleet/task-par1"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    return repo


def _make_response(content: str, tokens: int = 50) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="mock/model",
        tokens_used=tokens,
        tool_calls=None,
        raw_message={"role": "assistant", "content": content},
    )


class TestParallelStages:
    @patch("agent_fleet.core.orchestrator.LLMProvider")
    def test_backend_and_frontend_run_in_parallel(
        self, mock_provider_cls: MagicMock, test_repo: Path
    ) -> None:
        """Both backend and frontend should produce output when run in parallel."""
        mock_provider = MagicMock()
        mock_provider.complete.return_value = _make_response("No changes needed.", tokens=30)
        mock_provider_cls.return_value = mock_provider

        orch = FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "default.yaml",
            agents_dir=CONFIG_DIR / "agents",
            repo_path=test_repo,
        )

        state: FleetState = {
            "task_id": "par1",
            "repo": str(test_repo),
            "description": "Add multiply",
            "workflow_name": "default",
            "status": "running",
            "current_stage": "backend",
            "pending_stages": ["backend", "frontend"],
            "completed_stages": ["plan"],
            "retry_counts": {},
            "stage_outputs": {
                "plan": {"success": True, "output": "Plan: add multiply"},
            },
            "total_tokens": 200,
        }

        result = orch.execute_stage(state)

        # Both stages should have produced output
        assert "backend" in result["stage_outputs"]
        assert "frontend" in result["stage_outputs"]
        # Tokens should increase
        assert result["total_tokens"] > 200

    @patch("agent_fleet.core.orchestrator.LLMProvider")
    def test_parallel_gates_evaluate_both(
        self, mock_provider_cls: MagicMock, test_repo: Path
    ) -> None:
        """evaluate_gate should process all parallel stages."""
        mock_provider = MagicMock()
        mock_provider_cls.return_value = mock_provider

        orch = FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "default.yaml",
            agents_dir=CONFIG_DIR / "agents",
            repo_path=test_repo,
        )

        state: FleetState = {
            "task_id": "par2",
            "repo": str(test_repo),
            "description": "Test",
            "workflow_name": "default",
            "status": "running",
            "current_stage": "backend",
            "pending_stages": ["backend", "frontend"],
            "completed_stages": ["plan"],
            "retry_counts": {},
            "stage_outputs": {
                "backend": {"success": True, "output": "Done"},
                "frontend": {"success": True, "output": "Done"},
            },
        }

        result = orch.evaluate_gate(state)

        # Both should be completed (approval gates auto-approve for automated)
        assert "backend" in result["completed_stages"]
        assert "frontend" in result["completed_stages"]
