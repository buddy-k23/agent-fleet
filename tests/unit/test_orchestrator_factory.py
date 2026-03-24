"""Tests for OrchestratorFactory — builds StatusWriter from Supabase data."""

from unittest.mock import MagicMock

from agent_fleet.worker.orchestrator_factory import OrchestratorFactory
from agent_fleet.worker.status_writer import StatusWriter


def test_from_supabase_returns_status_writer():
    """Factory builds a StatusWriter from Supabase workflow + agent data."""
    workflow_data = {
        "name": "test-workflow",
        "stages": [
            {
                "name": "plan",
                "agent": "Architect",
                "gate": {"type": "approval"},
            }
        ],
    }
    agent_configs = [
        {
            "name": "Architect",
            "description": "Plans",
            "capabilities": ["code_analysis"],
            "tools": ["code"],
            "default_model": "anthropic/claude-opus-4-6",
            "system_prompt": "You are an architect.",
        }
    ]
    repos = {
        "tasks": MagicMock(),
        "executions": MagicMock(),
        "gate_results": MagicMock(),
        "events": MagicMock(),
    }

    writer = OrchestratorFactory.from_supabase(
        workflow_data=workflow_data,
        agent_configs=agent_configs,
        task_id="task-123",
        repos=repos,
    )

    assert isinstance(writer, StatusWriter)
    assert writer.workflow.name == "test-workflow"
    assert writer._registry.has("Architect")


def test_from_supabase_handles_full_workflow():
    """Factory handles multi-stage workflow with depends_on."""
    workflow_data = {
        "name": "full-pipeline",
        "concurrency": 1,
        "max_cost_usd": 5.0,
        "stages": [
            {"name": "plan", "agent": "Architect", "gate": {"type": "approval"}},
            {
                "name": "implement",
                "agent": "Backend",
                "depends_on": ["plan"],
                "gate": {"type": "automated", "checks": ["tests_pass"]},
            },
        ],
    }
    agent_configs = [
        {
            "name": "Architect",
            "description": "Plans",
            "capabilities": ["code_analysis"],
            "tools": ["code"],
            "default_model": "anthropic/claude-opus-4-6",
            "system_prompt": "Architect prompt",
        },
        {
            "name": "Backend",
            "description": "Codes",
            "capabilities": ["coding"],
            "tools": ["code", "shell"],
            "default_model": "anthropic/claude-sonnet-4-6",
            "system_prompt": "Backend prompt",
        },
    ]
    repos = {
        "tasks": MagicMock(),
        "executions": MagicMock(),
        "gate_results": MagicMock(),
        "events": MagicMock(),
    }

    writer = OrchestratorFactory.from_supabase(
        workflow_data=workflow_data,
        agent_configs=agent_configs,
        task_id="task-456",
        repos=repos,
    )

    assert writer.workflow.max_cost_usd == 5.0
    assert len(writer.workflow.stages) == 2
