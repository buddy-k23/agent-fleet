"""Smoke test — verify all layers integrate correctly."""

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_fleet.agents.registry import AgentRegistry
from agent_fleet.core.gates import evaluate_gate
from agent_fleet.core.orchestrator import build_orchestrator_graph
from agent_fleet.core.router import Router
from agent_fleet.core.workflow import load_workflow
from agent_fleet.main import create_app
from agent_fleet.models.provider import LLMResponse
from agent_fleet.workspace.worktree import WorktreeManager

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestRegistryAndWorkflow:
    """Verify agent registry and workflow config integrate."""

    def test_registry_loads_all_builtin_agents(self) -> None:
        registry = AgentRegistry(CONFIG_DIR / "agents")
        agents = registry.list_agents()
        assert len(agents) >= 6
        expected = {"architect", "backend-dev", "frontend-dev", "reviewer", "tester", "integrator"}
        assert expected.issubset(set(agents))  # core agents present
        # Banking agents may also be present

    def test_default_workflow_loads(self) -> None:
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        assert wf.name == "Full Development Pipeline"
        assert len(wf.stages) == 6

    def test_workflow_agents_exist_in_registry(self) -> None:
        registry = AgentRegistry(CONFIG_DIR / "agents")
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        for stage in wf.stages:
            assert registry.has(stage.agent), (
                f"Stage '{stage.name}' references agent '{stage.agent}' not in registry"
            )


class TestRouterAndGates:
    """Verify router resolves full pipeline and gates evaluate."""

    def test_router_resolves_full_pipeline(self) -> None:
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        router = Router(wf)
        completed: set[str] = set()

        # plan
        ready = router.get_next_stages(completed)
        assert {s.name for s in ready} == {"plan"}
        completed.add("plan")

        # backend + frontend (parallel)
        ready = router.get_next_stages(completed)
        assert {s.name for s in ready} == {"backend", "frontend"}
        completed.update(["backend", "frontend"])

        # review
        ready = router.get_next_stages(completed)
        assert {s.name for s in ready} == {"review"}
        completed.add("review")

        # e2e
        ready = router.get_next_stages(completed)
        assert {s.name for s in ready} == {"e2e"}
        completed.add("e2e")

        # deliver
        ready = router.get_next_stages(completed)
        assert {s.name for s in ready} == {"deliver"}
        completed.add("deliver")

        assert router.is_complete(completed)

    def test_review_gate_evaluates(self) -> None:
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        review = wf.get_stage("review")

        passing = evaluate_gate(review.gate, score=90)
        assert passing.passed is True

        failing = evaluate_gate(review.gate, score=60)
        assert failing.passed is False


class TestOrchestrator:
    """Verify LangGraph orchestrator compiles."""

    def test_orchestrator_graph_compiles(self) -> None:
        graph = build_orchestrator_graph()
        assert graph is not None

    def test_graph_has_all_nodes(self) -> None:
        graph = build_orchestrator_graph()
        node_names = set(graph.get_graph().nodes.keys())
        assert "route_next" in node_names
        assert "execute_stage" in node_names
        assert "evaluate_gate" in node_names


class TestAPILifecycle:
    """Verify API task lifecycle end-to-end."""

    def test_submit_get_list(self) -> None:
        app = create_app(database_url="sqlite:///:memory:")
        with TestClient(app) as client:
            # Health
            resp = client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

            # Submit
            resp = client.post(
                "/api/v1/tasks",
                json={
                    "repo": "/test/repo",
                    "description": "Integration test task",
                    "workflow": "default",
                },
            )
            assert resp.status_code == 201
            task_id = resp.json()["task_id"]

            # Get
            resp = client.get(f"/api/v1/tasks/{task_id}")
            assert resp.status_code == 200
            assert resp.json()["status"] == "queued"

            # List
            resp = client.get("/api/v1/tasks")
            assert resp.status_code == 200
            assert len(resp.json()["tasks"]) >= 1

            # 404
            resp = client.get("/api/v1/tasks/nonexistent")
            assert resp.status_code == 404


class TestWorktreeIntegration:
    """Verify worktree create and cleanup in a real git repo."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        return tmp_path

    def test_worktree_create_and_cleanup(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        wt = mgr.create(task_id="smoke-001", stage="plan")
        assert wt.exists()
        assert (wt / "README.md").exists()
        mgr.cleanup(wt)
        assert not wt.exists()

    def test_worktree_on_correct_branch(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        wt = mgr.create(task_id="smoke-002", stage="backend")
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=wt,
            capture_output=True,
            text=True,
        )
        assert "fleet/smoke-002-backend" in result.stdout
        mgr.cleanup(wt)


class TestLLMProviderModel:
    """Verify LLMResponse model works."""

    def test_llm_response_serializes(self) -> None:
        resp = LLMResponse(
            content="Hello",
            model="anthropic/claude-sonnet-4-6",
            tokens_used=100,
            cost_usd=0.001,
        )
        data = resp.model_dump()
        assert data["content"] == "Hello"
        assert data["tokens_used"] == 100
