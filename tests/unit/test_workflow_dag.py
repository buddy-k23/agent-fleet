"""Tests for DAG-based stage resolution and default workflow."""

from pathlib import Path

from agent_fleet.core.workflow import load_workflow

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "workflows"
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestDAGResolution:
    def test_first_stage_has_no_deps(self) -> None:
        wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
        ready = wf.get_ready_stages(completed=set())
        assert len(ready) == 1
        assert ready[0].name == "plan"

    def test_parallel_stages_after_plan(self) -> None:
        wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
        ready = wf.get_ready_stages(completed={"plan"})
        names = {s.name for s in ready}
        assert names == {"backend", "frontend"}

    def test_review_only_after_both_parallel(self) -> None:
        wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
        # Only backend done — frontend not yet
        ready = wf.get_ready_stages(completed={"plan", "backend"})
        names = {s.name for s in ready}
        assert "review" not in names
        assert "frontend" in names

    def test_review_after_both_parallel_complete(self) -> None:
        wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
        ready = wf.get_ready_stages(completed={"plan", "backend", "frontend"})
        assert len(ready) == 1
        assert ready[0].name == "review"

    def test_all_done_returns_empty(self) -> None:
        wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
        ready = wf.get_ready_stages(
            completed={"plan", "backend", "frontend", "review"}
        )
        assert len(ready) == 0

    def test_completed_stages_not_returned(self) -> None:
        wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
        ready = wf.get_ready_stages(completed={"plan"})
        names = {s.name for s in ready}
        assert "plan" not in names


class TestDefaultWorkflow:
    def test_default_workflow_loads(self) -> None:
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        assert wf.name == "Full Development Pipeline"
        assert len(wf.stages) == 6

    def test_default_workflow_concurrency(self) -> None:
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        assert wf.concurrency == 1
        assert wf.max_cost_usd == 50.0
        assert wf.classifier_mode == "suggest"

    def test_default_workflow_stage_order(self) -> None:
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        stage_names = [s.name for s in wf.stages]
        assert stage_names == ["plan", "backend", "frontend", "review", "e2e", "deliver"]

    def test_default_workflow_parallel_detection(self) -> None:
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        ready = wf.get_ready_stages(completed={"plan"})
        names = {s.name for s in ready}
        assert names == {"backend", "frontend"}

    def test_default_workflow_full_walkthrough(self) -> None:
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        completed: set[str] = set()

        # Step 1: plan
        ready = wf.get_ready_stages(completed)
        assert {s.name for s in ready} == {"plan"}
        completed.add("plan")

        # Step 2: backend + frontend (parallel)
        ready = wf.get_ready_stages(completed)
        assert {s.name for s in ready} == {"backend", "frontend"}
        completed.update(["backend", "frontend"])

        # Step 3: review
        ready = wf.get_ready_stages(completed)
        assert {s.name for s in ready} == {"review"}
        completed.add("review")

        # Step 4: e2e
        ready = wf.get_ready_stages(completed)
        assert {s.name for s in ready} == {"e2e"}
        completed.add("e2e")

        # Step 5: deliver
        ready = wf.get_ready_stages(completed)
        assert {s.name for s in ready} == {"deliver"}
        completed.add("deliver")

        # Done
        assert wf.get_ready_stages(completed) == []

    def test_default_workflow_agents_are_valid_names(self) -> None:
        """Agents referenced in default workflow must match built-in agent filenames."""
        from agent_fleet.agents.registry import AgentRegistry

        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        registry = AgentRegistry(CONFIG_DIR / "agents")
        for stage in wf.stages:
            assert registry.has(stage.agent), (
                f"Stage '{stage.name}' references agent '{stage.agent}' "
                f"which is not in the registry"
            )

    def test_default_workflow_review_gate(self) -> None:
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        review = wf.get_stage("review")
        assert review.gate.type == "score"
        assert review.gate.min_score == 80
        assert review.gate.on_fail == "route_to"
        # route_target now comes from reviewer JSON, not config
        assert review.gate.max_retries == 2
