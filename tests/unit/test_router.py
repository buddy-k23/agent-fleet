"""Tests for DAG-based stage router."""

from pathlib import Path

from agent_fleet.core.router import Router
from agent_fleet.core.workflow import load_workflow

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "workflows"


def test_first_stage_is_plan() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    next_stages = router.get_next_stages(completed=set())
    assert len(next_stages) == 1
    assert next_stages[0].name == "plan"


def test_parallel_stages_after_plan() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    next_stages = router.get_next_stages(completed={"plan"})
    names = {s.name for s in next_stages}
    assert names == {"backend", "frontend"}


def test_review_after_both_parallel() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    next_stages = router.get_next_stages(completed={"plan", "backend", "frontend"})
    assert len(next_stages) == 1
    assert next_stages[0].name == "review"


def test_all_done_returns_empty() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    next_stages = router.get_next_stages(
        completed={"plan", "backend", "frontend", "review"}
    )
    assert len(next_stages) == 0


def test_route_back_target() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    target = router.get_route_back_target("review")
    assert target == "backend"


def test_route_back_target_none_for_retry() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    target = router.get_route_back_target("plan")
    assert target is None


def test_is_complete_true() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    assert router.is_complete({"plan", "backend", "frontend", "review"}) is True


def test_is_complete_false() -> None:
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    assert router.is_complete({"plan", "backend"}) is False
