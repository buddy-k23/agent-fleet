"""Tests for wired orchestrator node functions."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_fleet.agents.result import AgentResult
from agent_fleet.core.orchestrator import FleetOrchestrator
from agent_fleet.core.state import FleetState

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestRouteNext:
    def _make_orchestrator(self) -> FleetOrchestrator:
        return FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "two-stage.yaml",
            agents_dir=CONFIG_DIR / "agents",
        )

    def test_routes_to_first_stage(self) -> None:
        orch = self._make_orchestrator()
        state: FleetState = {
            "task_id": "t1",
            "repo": "/r",
            "description": "Test",
            "workflow_name": "two-stage",
            "status": "running",
            "completed_stages": [],
        }
        result = orch.route_next(state)
        assert result["current_stage"] == "plan"

    def test_routes_to_second_stage_after_plan(self) -> None:
        orch = self._make_orchestrator()
        state: FleetState = {
            "task_id": "t1",
            "repo": "/r",
            "description": "Test",
            "workflow_name": "two-stage",
            "status": "running",
            "completed_stages": ["plan"],
        }
        result = orch.route_next(state)
        assert result["current_stage"] == "backend"

    def test_sets_completed_when_all_done(self) -> None:
        orch = self._make_orchestrator()
        state: FleetState = {
            "task_id": "t1",
            "repo": "/r",
            "description": "Test",
            "workflow_name": "two-stage",
            "status": "running",
            "completed_stages": ["plan", "backend"],
        }
        result = orch.route_next(state)
        assert result["status"] == "completed"


class TestExecuteStage:
    def _make_git_repo(self, tmp_path: Path) -> Path:
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        return tmp_path

    @patch("agent_fleet.core.orchestrator.AgentRunner")
    def test_execute_stage_runs_agent(
        self, mock_runner_cls: MagicMock, tmp_path: Path
    ) -> None:
        repo = self._make_git_repo(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = AgentResult(
            success=True,
            output="Plan: add multiply function",
            files_changed=[],
            tokens_used=500,
            iterations=2,
            tool_calls=[],
        )
        mock_runner_cls.return_value = mock_runner

        orch = FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "two-stage.yaml",
            agents_dir=CONFIG_DIR / "agents",
            repo_path=repo,
        )
        state: FleetState = {
            "task_id": "t-exec",
            "repo": str(repo),
            "description": "Add multiply",
            "workflow_name": "two-stage",
            "status": "running",
            "current_stage": "plan",
            "completed_stages": [],
            "stage_outputs": {},
            "total_tokens": 0,
        }
        result = orch.execute_stage(state)

        assert "plan" in result["stage_outputs"]
        assert result["stage_outputs"]["plan"]["success"] is True
        assert result["total_tokens"] == 500
        mock_runner.run.assert_called_once()

    @patch("agent_fleet.core.orchestrator.AgentRunner")
    def test_execute_stage_includes_plan_in_context(
        self, mock_runner_cls: MagicMock, tmp_path: Path
    ) -> None:
        repo = self._make_git_repo(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = AgentResult(
            success=True,
            output="Implemented multiply",
            files_changed=["calculator.py"],
            tokens_used=800,
            iterations=3,
            tool_calls=[],
        )
        mock_runner_cls.return_value = mock_runner

        orch = FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "two-stage.yaml",
            agents_dir=CONFIG_DIR / "agents",
            repo_path=repo,
        )
        state: FleetState = {
            "task_id": "t-ctx",
            "repo": str(repo),
            "description": "Add multiply",
            "workflow_name": "two-stage",
            "status": "running",
            "current_stage": "backend",
            "completed_stages": ["plan"],
            "stage_outputs": {
                "plan": {
                    "success": True,
                    "output": "## Plan\nAdd multiply to calculator.py",
                    "files_changed": [],
                    "tokens_used": 500,
                    "iterations": 2,
                    "tool_calls": [],
                }
            },
            "total_tokens": 500,
        }
        orch.execute_stage(state)

        # Verify the plan was passed in the task context
        call_args = mock_runner.run.call_args
        task_context = call_args[0][1]  # second positional arg
        assert "Plan" in task_context
        assert "multiply" in task_context
