"""Tests for StatusWriter — orchestrator persistence layer."""

from unittest.mock import MagicMock, patch

import pytest

from agent_fleet.worker.status_writer import StatusWriter


@pytest.fixture
def mock_repos():
    """Create mock Supabase repositories."""
    return {
        "tasks": MagicMock(),
        "executions": MagicMock(),
        "gate_results": MagicMock(),
        "events": MagicMock(),
    }


@pytest.fixture
def mock_workflow():
    """Minimal workflow config for testing."""
    from agent_fleet.core.workflow import GateConfig, StageConfig, WorkflowConfig

    return WorkflowConfig(
        name="test-workflow",
        stages=[
            StageConfig(
                name="plan",
                agent="Architect",
                gate=GateConfig(type="approval"),
            ),
            StageConfig(
                name="implement",
                agent="Backend",
                depends_on=["plan"],
                gate=GateConfig(type="automated", checks=["tests_pass"]),
            ),
        ],
    )


@pytest.fixture
def mock_registry():
    """Minimal agent registry for testing."""
    from agent_fleet.agents.registry import AgentRegistry

    return AgentRegistry.from_configs([
        {
            "name": "Architect",
            "description": "Plans",
            "capabilities": ["code_analysis"],
            "tools": ["code"],
            "default_model": "anthropic/claude-opus-4-6",
            "system_prompt": "You are an architect.",
        },
        {
            "name": "Backend",
            "description": "Implements",
            "capabilities": ["coding"],
            "tools": ["code", "shell"],
            "default_model": "anthropic/claude-sonnet-4-6",
            "system_prompt": "You are a developer.",
        },
    ])


class TestRouteNext:
    def test_route_next_writes_current_stage(self, mock_repos, mock_workflow, mock_registry):
        """route_next writes current_stage to Supabase tasks table."""
        writer = StatusWriter(
            repos=mock_repos,
            task_id="task-1",
            workflow=mock_workflow,
            registry=mock_registry,
        )
        state = {
            "task_id": "task-1",
            "status": "running",
            "completed_stages": [],
        }
        mock_repos["tasks"].get.return_value = {"status": "running"}

        with patch.object(writer.__class__.__bases__[0], "route_next") as mock_super:
            mock_super.return_value = {**state, "current_stage": "plan", "pending_stages": ["plan"]}
            result = writer.route_next(state)

        mock_repos["tasks"].update_status.assert_called_once()
        assert result["current_stage"] == "plan"

    def test_route_next_detects_cancellation(self, mock_repos, mock_workflow, mock_registry):
        """route_next returns interrupted state if task is cancelled."""
        writer = StatusWriter(
            repos=mock_repos,
            task_id="task-1",
            workflow=mock_workflow,
            registry=mock_registry,
        )
        state = {"task_id": "task-1", "status": "running", "completed_stages": []}
        mock_repos["tasks"].get.return_value = {"status": "cancelled"}

        result = writer.route_next(state)
        assert result["status"] == "interrupted"

    def test_route_next_appends_event(self, mock_repos, mock_workflow, mock_registry):
        """route_next appends a route event to Supabase."""
        writer = StatusWriter(
            repos=mock_repos,
            task_id="task-1",
            workflow=mock_workflow,
            registry=mock_registry,
        )
        state = {"task_id": "task-1", "status": "running", "completed_stages": []}
        mock_repos["tasks"].get.return_value = {"status": "running"}

        with patch.object(writer.__class__.__bases__[0], "route_next") as mock_super:
            mock_super.return_value = {**state, "current_stage": "plan"}
            writer.route_next(state)

        mock_repos["events"].append.assert_called()


class TestExecuteStage:
    def test_execute_stage_creates_and_updates_execution(self, mock_repos, mock_workflow, mock_registry):
        """execute_stage creates execution row before, updates after."""
        writer = StatusWriter(
            repos=mock_repos,
            task_id="task-1",
            workflow=mock_workflow,
            registry=mock_registry,
        )
        state = {
            "task_id": "task-1",
            "current_stage": "plan",
            "pending_stages": ["plan"],
            "completed_stages": [],
        }
        mock_repos["executions"].create.return_value = {"id": "ex-1"}

        with patch.object(writer.__class__.__bases__[0], "execute_stage") as mock_super:
            mock_super.return_value = {
                **state,
                "stage_outputs": {"plan": {"output": "done"}},
                "total_tokens": 1000,
            }
            result = writer.execute_stage(state)

        mock_repos["executions"].create.assert_called_once()
        mock_repos["executions"].update_status.assert_called_once()
        assert result["total_tokens"] == 1000

    def test_execute_stage_writes_error_on_failure(self, mock_repos, mock_workflow, mock_registry):
        """execute_stage writes error status if super raises."""
        writer = StatusWriter(
            repos=mock_repos,
            task_id="task-1",
            workflow=mock_workflow,
            registry=mock_registry,
        )
        state = {
            "task_id": "task-1",
            "current_stage": "plan",
            "pending_stages": ["plan"],
            "completed_stages": [],
        }
        mock_repos["executions"].create.return_value = {"id": "ex-1"}

        with patch.object(writer.__class__.__bases__[0], "execute_stage") as mock_super:
            mock_super.side_effect = RuntimeError("LLM failed")
            result = writer.execute_stage(state)

        mock_repos["executions"].update_status.assert_called_once()
        update_call = mock_repos["executions"].update_status.call_args
        assert update_call[1]["status"] == "error" or update_call[0][1] == "error"


class TestEvaluateGate:
    def test_evaluate_gate_writes_result(self, mock_repos, mock_workflow, mock_registry):
        """evaluate_gate writes gate_result to Supabase."""
        writer = StatusWriter(
            repos=mock_repos,
            task_id="task-1",
            workflow=mock_workflow,
            registry=mock_registry,
        )
        state = {
            "task_id": "task-1",
            "current_stage": "plan",
            "completed_stages": [],
        }
        writer._current_execution_id = "ex-1"

        with patch.object(writer.__class__.__bases__[0], "evaluate_gate") as mock_super:
            mock_super.return_value = {**state, "completed_stages": ["plan"]}
            result = writer.evaluate_gate(state)

        mock_repos["gate_results"].create.assert_called_once()
        assert "plan" in result["completed_stages"]
