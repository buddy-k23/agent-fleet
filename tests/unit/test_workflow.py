"""Tests for workflow config models and YAML loader."""

from pathlib import Path

import pytest

from agent_fleet.core.workflow import GateConfig, StageConfig, WorkflowConfig, load_workflow

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "workflows"


def test_load_workflow_from_yaml() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    assert wf.name == "Test Pipeline"
    assert wf.concurrency == 1
    assert wf.max_cost_usd == 10.0
    assert wf.classifier_mode == "suggest"
    assert len(wf.stages) == 4


def test_stage_depends_on_normalized_none_to_empty_list() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    plan = wf.get_stage("plan")
    assert plan.depends_on == []


def test_stage_depends_on_normalized_string_to_list() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    backend = wf.get_stage("backend")
    assert backend.depends_on == ["plan"]


def test_stage_depends_on_list_preserved() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    review = wf.get_stage("review")
    assert set(review.depends_on) == {"backend", "frontend"}


def test_gate_config_parsed() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    review = wf.get_stage("review")
    assert review.gate.type == "score"
    assert review.gate.min_score == 80
    assert review.gate.on_fail == "route_to"
    assert review.gate.route_target == "backend"


def test_gate_config_defaults() -> None:
    gate = GateConfig(type="automated")
    assert gate.checks == []
    assert gate.min_score is None
    assert gate.scored_by == "reviewer"
    assert gate.on_fail == "retry"
    assert gate.route_target is None
    assert gate.max_retries is None


def test_get_stage_raises_for_missing() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    with pytest.raises(ValueError, match="Stage not found"):
        wf.get_stage("nonexistent")


def test_workflow_defaults() -> None:
    wf = WorkflowConfig(
        name="Minimal",
        stages=[StageConfig(name="only", agent="test")],
    )
    assert wf.concurrency == 1
    assert wf.max_cost_usd is None
    assert wf.classifier_mode == "suggest"


def test_stage_defaults() -> None:
    stage = StageConfig(name="test", agent="test-agent")
    assert stage.model is None
    assert stage.depends_on == []
    assert stage.gate.type == "automated"
    assert stage.reactions == {}
    assert stage.actions == []
