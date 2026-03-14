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


class TestEvaluateGate:
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

    def test_approval_gate_auto_approves(self, tmp_path: Path) -> None:
        repo = self._make_git_repo(tmp_path)
        orch = FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "two-stage.yaml",
            agents_dir=CONFIG_DIR / "agents",
            repo_path=repo,
        )
        state: FleetState = {
            "task_id": "t-gate-a",
            "repo": str(repo),
            "description": "Test",
            "workflow_name": "two-stage",
            "status": "running",
            "current_stage": "plan",
            "completed_stages": [],
            "stage_outputs": {"plan": {"success": True, "output": "Plan here"}},
            "retry_counts": {},
        }
        result = orch.evaluate_gate(state)
        assert "plan" in result["completed_stages"]

    def test_automated_gate_passes_when_tests_pass(self, tmp_path: Path) -> None:
        repo = self._make_git_repo(tmp_path)

        # Create a worktree with passing tests
        worktree = tmp_path / ".fleet-worktrees" / "fleet-worktree-t-gate-b-backend"
        worktree.mkdir(parents=True)
        # Simulate worktree as git repo
        subprocess.run(["git", "init"], cwd=worktree, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=worktree, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=worktree, capture_output=True, check=True,
        )
        # Write a passing test
        (worktree / "test_pass.py").write_text("def test_ok():\n    assert True\n")
        subprocess.run(["git", "add", "."], cwd=worktree, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test"],
            cwd=worktree, capture_output=True, check=True,
        )

        orch = FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "two-stage.yaml",
            agents_dir=CONFIG_DIR / "agents",
            repo_path=repo,
        )
        state: FleetState = {
            "task_id": "t-gate-b",
            "repo": str(repo),
            "description": "Test",
            "workflow_name": "two-stage",
            "status": "running",
            "current_stage": "backend",
            "completed_stages": ["plan"],
            "stage_outputs": {"backend": {"success": True, "output": "Done"}},
            "retry_counts": {},
            "_worktree_path": str(worktree),
        }
        result = orch.evaluate_gate(state)
        assert "backend" in result["completed_stages"]

    def test_automated_gate_fails_when_tests_fail(self, tmp_path: Path) -> None:
        repo = self._make_git_repo(tmp_path)

        worktree = tmp_path / ".fleet-worktrees" / "fleet-worktree-t-gate-c-backend"
        worktree.mkdir(parents=True)
        subprocess.run(["git", "init"], cwd=worktree, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=worktree, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=worktree, capture_output=True, check=True,
        )
        # Write a failing test
        (worktree / "test_fail.py").write_text("def test_bad():\n    assert False\n")
        subprocess.run(["git", "add", "."], cwd=worktree, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test"],
            cwd=worktree, capture_output=True, check=True,
        )

        orch = FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "two-stage.yaml",
            agents_dir=CONFIG_DIR / "agents",
            repo_path=repo,
        )
        state: FleetState = {
            "task_id": "t-gate-c",
            "repo": str(repo),
            "description": "Test",
            "workflow_name": "two-stage",
            "status": "running",
            "current_stage": "backend",
            "completed_stages": ["plan"],
            "stage_outputs": {"backend": {"success": True, "output": "Done"}},
            "retry_counts": {},
            "_worktree_path": str(worktree),
        }
        result = orch.evaluate_gate(state)
        # Should NOT be in completed_stages
        assert "backend" not in result.get("completed_stages", [])
        # Retry count incremented
        assert result["retry_counts"].get("backend", 0) >= 1

    def test_gate_sets_error_after_max_retries(self, tmp_path: Path) -> None:
        repo = self._make_git_repo(tmp_path)

        worktree = tmp_path / ".fleet-worktrees" / "fleet-worktree-t-gate-d-backend"
        worktree.mkdir(parents=True)
        subprocess.run(["git", "init"], cwd=worktree, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=worktree, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=worktree, capture_output=True, check=True,
        )
        (worktree / "test_fail.py").write_text("def test_bad():\n    assert False\n")
        subprocess.run(["git", "add", "."], cwd=worktree, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test"],
            cwd=worktree, capture_output=True, check=True,
        )

        orch = FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "two-stage.yaml",
            agents_dir=CONFIG_DIR / "agents",
            repo_path=repo,
        )
        state: FleetState = {
            "task_id": "t-gate-d",
            "repo": str(repo),
            "description": "Test",
            "workflow_name": "two-stage",
            "status": "running",
            "current_stage": "backend",
            "completed_stages": ["plan"],
            "stage_outputs": {"backend": {"success": True, "output": "Done"}},
            "retry_counts": {"backend": 3},  # Already at max
            "_worktree_path": str(worktree),
        }
        result = orch.evaluate_gate(state)
        assert result["status"] == "error"


class TestScoreGate:
    def _make_orchestrator(self) -> FleetOrchestrator:
        return FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "default.yaml",
            agents_dir=CONFIG_DIR / "agents",
        )

    def test_score_gate_passes_above_threshold(self) -> None:
        import json

        orch = self._make_orchestrator()
        review_output = json.dumps({
            "score": 90,
            "reasoning": "Code looks great",
            "issues": [],
        })
        state: FleetState = {
            "task_id": "t-score-a",
            "repo": "/r",
            "description": "Test",
            "workflow_name": "default",
            "status": "running",
            "current_stage": "review",
            "completed_stages": ["plan", "backend", "frontend"],
            "stage_outputs": {"review": {"success": True, "output": review_output}},
            "retry_counts": {},
        }
        result = orch.evaluate_gate(state)
        assert "review" in result["completed_stages"]

    def test_score_gate_fails_and_routes_to_stage_from_json(self) -> None:
        import json

        orch = self._make_orchestrator()
        review_output = json.dumps({
            "score": 60,
            "reasoning": "Missing tests",
            "issues": [{"description": "No edge cases"}],
            "route_to": "backend",
        })
        state: FleetState = {
            "task_id": "t-score-b",
            "repo": "/r",
            "description": "Test",
            "workflow_name": "default",
            "status": "running",
            "current_stage": "review",
            "completed_stages": ["plan", "backend", "frontend"],
            "stage_outputs": {"review": {"success": True, "output": review_output}},
            "retry_counts": {},
        }
        result = orch.evaluate_gate(state)
        assert "review" not in result["completed_stages"]
        # backend should be removed from completed so it re-executes
        assert "backend" not in result["completed_stages"]
        assert result["retry_counts"].get("review", 0) >= 1

    def test_score_gate_falls_back_to_config_route_target(self) -> None:
        import json

        orch = self._make_orchestrator()
        # No route_to in reviewer JSON
        review_output = json.dumps({
            "score": 50,
            "reasoning": "Poor quality",
            "issues": [],
        })
        state: FleetState = {
            "task_id": "t-score-c",
            "repo": "/r",
            "description": "Test",
            "workflow_name": "default",
            "status": "running",
            "current_stage": "review",
            "completed_stages": ["plan", "backend", "frontend"],
            "stage_outputs": {"review": {"success": True, "output": review_output}},
            "retry_counts": {},
        }
        result = orch.evaluate_gate(state)
        assert "review" not in result["completed_stages"]
        # Should still route back (to first depends_on or config target)
        assert result["retry_counts"].get("review", 0) >= 1

    def test_score_gate_malformed_json_treated_as_zero(self) -> None:
        orch = self._make_orchestrator()
        state: FleetState = {
            "task_id": "t-score-d",
            "repo": "/r",
            "description": "Test",
            "workflow_name": "default",
            "status": "running",
            "current_stage": "review",
            "completed_stages": ["plan", "backend", "frontend"],
            "stage_outputs": {"review": {"success": True, "output": "not json at all"}},
            "retry_counts": {},
        }
        result = orch.evaluate_gate(state)
        assert "review" not in result["completed_stages"]
