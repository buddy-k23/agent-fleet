"""Tests for agent + workflow recommendation."""

from agent_fleet.onboarding.recommender import recommend_agents, recommend_workflow
from agent_fleet.onboarding.scanner import ProjectProfile


def _make_profile(**kwargs) -> ProjectProfile:  # type: ignore[no-untyped-def]
    defaults = {
        "name": "test",
        "repo_path": "/test",
        "languages": ["python"],
        "frameworks": ["fastapi"],
        "test_frameworks": ["pytest"],
        "databases": [],
        "package_managers": ["pip"],
        "has_ci": False,
        "ci_platform": None,
        "has_claude_md": False,
        "has_docker": False,
        "estimated_loc": 1000,
        "entry_points": [],
        "metadata": {},
    }
    defaults.update(kwargs)
    return ProjectProfile(**defaults)


class TestRecommendAgents:
    def test_backend_only_skips_frontend(self) -> None:
        profile = _make_profile(frameworks=["fastapi"])
        agents = recommend_agents(profile)
        names = [a["name"] for a in agents]
        assert "Backend Dev" in names
        assert "Frontend Dev" not in names

    def test_fullstack_includes_frontend(self) -> None:
        profile = _make_profile(frameworks=["fastapi", "react"])
        agents = recommend_agents(profile)
        names = [a["name"] for a in agents]
        assert "Frontend Dev" in names
        assert "Backend Dev" in names

    def test_reviewer_uses_sonnet_not_haiku(self) -> None:
        profile = _make_profile()
        agents = recommend_agents(profile)
        reviewer = next(a for a in agents if a["name"] == "Reviewer")
        assert "haiku" not in reviewer["model"]
        assert "sonnet" in reviewer["model"]

    def test_tester_uses_haiku(self) -> None:
        profile = _make_profile()
        agents = recommend_agents(profile)
        tester = next(a for a in agents if a["name"] == "Tester")
        assert "haiku" in tester["model"]

    def test_always_includes_architect_integrator(self) -> None:
        profile = _make_profile()
        agents = recommend_agents(profile)
        names = [a["name"] for a in agents]
        assert "Architect" in names
        assert "Integrator" in names


class TestRecommendWorkflow:
    def test_fullstack_gets_6_stages(self) -> None:
        profile = _make_profile(frameworks=["fastapi", "react"])
        wf = recommend_workflow(profile)
        assert len(wf["stages"]) == 6
        assert wf["name"] == "Full Development Pipeline"

    def test_backend_only_gets_5_stages(self) -> None:
        profile = _make_profile(frameworks=["fastapi"])
        wf = recommend_workflow(profile)
        assert len(wf["stages"]) == 5
        assert wf["name"] == "Backend Pipeline"

    def test_no_tests_gets_minimal(self) -> None:
        profile = _make_profile(test_frameworks=[])
        wf = recommend_workflow(profile)
        assert wf["name"] == "Minimal Pipeline"
        assert len(wf["stages"]) == 4

    def test_max_iterations_set_per_stage(self) -> None:
        profile = _make_profile()
        wf = recommend_workflow(profile)
        plan = next(s for s in wf["stages"] if s["name"] == "plan")
        assert plan["max_iterations"] == 10
