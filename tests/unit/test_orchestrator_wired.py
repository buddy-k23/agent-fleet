"""Tests for wired orchestrator node functions."""

from pathlib import Path

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
