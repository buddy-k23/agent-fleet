"""Tests for LangGraph orchestrator graph."""

import pytest

from agent_fleet.core.events import log_event
from agent_fleet.core.orchestrator import build_orchestrator_graph, should_continue
from agent_fleet.core.state import FleetState


def test_graph_builds_without_error() -> None:
    graph = build_orchestrator_graph()
    assert graph is not None


def test_graph_has_expected_nodes() -> None:
    graph = build_orchestrator_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "route_next" in node_names
    assert "execute_stage" in node_names
    assert "evaluate_gate" in node_names


def test_should_continue_returns_route_next_when_running() -> None:
    state: FleetState = {
        "task_id": "t1",
        "repo": "/r",
        "description": "d",
        "workflow_name": "default",
        "status": "running",
    }
    assert should_continue(state) == "route_next"


def test_should_continue_returns_end_when_completed() -> None:
    state: FleetState = {
        "task_id": "t1",
        "repo": "/r",
        "description": "d",
        "workflow_name": "default",
        "status": "completed",
    }
    assert should_continue(state) == "__end__"


def test_should_continue_returns_end_when_error() -> None:
    state: FleetState = {
        "task_id": "t1",
        "repo": "/r",
        "description": "d",
        "workflow_name": "default",
        "status": "error",
    }
    assert should_continue(state) == "__end__"


def test_should_continue_returns_end_when_cost_limit() -> None:
    state: FleetState = {
        "task_id": "t1",
        "repo": "/r",
        "description": "d",
        "workflow_name": "default",
        "status": "cost_limit",
    }
    assert should_continue(state) == "__end__"


def test_orchestrator_accepts_in_memory_config() -> None:
    """FleetOrchestrator can be constructed with in-memory workflow + registry."""
    from agent_fleet.agents.registry import AgentRegistry
    from agent_fleet.core.orchestrator import FleetOrchestrator
    from agent_fleet.core.workflow import GateConfig, StageConfig, WorkflowConfig

    workflow = WorkflowConfig(
        name="test-workflow",
        stages=[
            StageConfig(
                name="plan",
                agent="Architect",
                gate=GateConfig(type="approval"),
            )
        ],
    )
    registry = AgentRegistry.from_configs(
        [
            {
                "name": "Architect",
                "description": "Plans",
                "capabilities": ["code_analysis"],
                "tools": ["code"],
                "default_model": "anthropic/claude-opus-4-6",
                "system_prompt": "You are an architect.",
            }
        ]
    )

    orch = FleetOrchestrator(
        task_id="test-task-1",
        workflow=workflow,
        registry=registry,
    )
    assert orch.workflow.name == "test-workflow"
    assert orch._registry.has("Architect")


def test_orchestrator_rejects_incomplete_args() -> None:
    """FleetOrchestrator raises ValueError if neither config mode is complete."""
    from agent_fleet.core.orchestrator import FleetOrchestrator

    with pytest.raises(ValueError, match="Provide either"):
        FleetOrchestrator(task_id="test-task-1")


class TestEventLog:
    def test_log_event_returns_dict(self) -> None:
        event = log_event("task-001", "action", {"tool": "code"})
        assert event["task_id"] == "task-001"
        assert event["event_type"] == "action"
        assert event["payload"]["tool"] == "code"

    def test_log_event_includes_all_fields(self) -> None:
        event = log_event("t2", "observation", {"result": "ok"})
        assert "task_id" in event
        assert "event_type" in event
        assert "payload" in event
