"""Tests for LangGraph state schema."""

from agent_fleet.core.state import FleetState


def test_initial_state() -> None:
    state: FleetState = {
        "task_id": "task-001",
        "repo": "/path/to/repo",
        "description": "Implement feature",
        "workflow_name": "default",
        "status": "queued",
        "current_stage": None,
        "completed_stages": [],
        "retry_counts": {},
        "stage_outputs": {},
        "stage_errors": {},
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "pr_url": None,
        "error_message": None,
    }
    assert state["status"] == "queued"
    assert state["completed_stages"] == []
    assert state["current_stage"] is None
    assert state["retry_counts"] == {}


def test_state_tracks_completed_stages() -> None:
    state: FleetState = {
        "task_id": "task-002",
        "repo": "/path",
        "description": "Test",
        "workflow_name": "default",
        "status": "running",
        "completed_stages": ["plan", "backend"],
        "retry_counts": {"review": 1},
        "stage_outputs": {"plan": {"subtasks": ["a", "b"]}},
        "stage_errors": {},
        "total_tokens": 5000,
        "total_cost_usd": 0.15,
    }
    assert "plan" in state["completed_stages"]
    assert len(state["completed_stages"]) == 2
    assert state["total_tokens"] == 5000


def test_state_minimal_required_fields() -> None:
    """FleetState is total=False, so only required fields needed."""
    state: FleetState = {
        "task_id": "task-003",
        "repo": "/r",
        "description": "Minimal",
        "workflow_name": "default",
    }
    assert state["task_id"] == "task-003"
