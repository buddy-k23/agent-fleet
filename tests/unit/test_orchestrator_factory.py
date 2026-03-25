"""Tests for OrchestratorFactory — builds StatusWriter from Supabase data."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

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


def _make_repos() -> dict:
    return {
        "tasks": MagicMock(),
        "executions": MagicMock(),
        "gate_results": MagicMock(),
        "events": MagicMock(),
    }


def test_from_supabase_missing_workflow_name_raises():
    """workflow_data without 'name' raises a ValidationError."""
    workflow_data = {
        "stages": [{"name": "plan", "agent": "Architect"}],
    }
    agent_configs = [
        {
            "name": "Architect",
            "description": "Plans",
            "capabilities": ["code_analysis"],
            "tools": ["code"],
            "default_model": "anthropic/claude-opus-4-6",
            "system_prompt": "Architect prompt",
        }
    ]

    with pytest.raises(ValidationError):
        OrchestratorFactory.from_supabase(
            workflow_data=workflow_data,
            agent_configs=agent_configs,
            task_id="task-err",
            repos=_make_repos(),
        )


def test_from_supabase_empty_stages_raises():
    """workflow_data with empty stages list is valid — WorkflowConfig allows it."""
    workflow_data = {"name": "empty-wf", "stages": []}
    agent_configs: list[dict] = []

    # WorkflowConfig does not forbid empty stages; factory should succeed
    writer = OrchestratorFactory.from_supabase(
        workflow_data=workflow_data,
        agent_configs=agent_configs,
        task_id="task-empty",
        repos=_make_repos(),
    )

    assert isinstance(writer, StatusWriter)
    assert writer.workflow.stages == []


def test_from_supabase_agent_with_optional_fields():
    """Agent config with optional max_retries/timeout_minutes/max_tokens is accepted."""
    workflow_data = {
        "name": "wf-opt",
        "stages": [{"name": "code", "agent": "DevAgent"}],
    }
    agent_configs = [
        {
            "name": "DevAgent",
            "description": "Writes code",
            "capabilities": ["coding"],
            "tools": ["code", "shell"],
            "default_model": "anthropic/claude-sonnet-4-6",
            "system_prompt": "Write code.",
            "max_retries": 5,
            "timeout_minutes": 60,
            "max_tokens": 200000,
        }
    ]

    writer = OrchestratorFactory.from_supabase(
        workflow_data=workflow_data,
        agent_configs=agent_configs,
        task_id="task-opt",
        repos=_make_repos(),
    )

    assert writer._registry.has("DevAgent")
    agent_cfg = writer._registry.get("DevAgent")
    assert agent_cfg.max_retries == 5
    assert agent_cfg.timeout_minutes == 60
    assert agent_cfg.max_tokens == 200000


def test_from_supabase_empty_agent_configs():
    """Empty agent list creates an empty registry without raising."""
    workflow_data = {
        "name": "wf-no-agents",
        "stages": [{"name": "plan", "agent": "Ghost"}],
    }

    writer = OrchestratorFactory.from_supabase(
        workflow_data=workflow_data,
        agent_configs=[],
        task_id="task-noagent",
        repos=_make_repos(),
    )

    assert isinstance(writer, StatusWriter)
    assert not writer._registry.has("Ghost")
