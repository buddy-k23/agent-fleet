"""Tests for framework-specific CLAUDE.md sections."""

from agent_fleet.onboarding.claude_md_generator import generate_claude_md
from agent_fleet.onboarding.scanner import ProjectProfile


def _p(**kwargs) -> ProjectProfile:  # type: ignore[no-untyped-def]
    defaults = {
        "name": "test", "repo_path": "/t", "languages": ["python"],
        "frameworks": [], "test_frameworks": [], "databases": [],
        "package_managers": ["pip"], "has_ci": False, "ci_platform": None,
        "has_claude_md": False, "has_docker": False, "estimated_loc": 100,
        "entry_points": [], "metadata": {},
    }
    defaults.update(kwargs)
    return ProjectProfile(**defaults)


def test_spring_boot_pitfalls() -> None:
    md = generate_claude_md(_p(frameworks=["spring-boot"], languages=["java"]))
    assert "JdbcTemplate" in md or "Spring" in md


def test_react_pitfalls() -> None:
    md = generate_claude_md(_p(
        frameworks=["react"], languages=["typescript"],
    ))
    assert "data-testid" in md


def test_npm_commands() -> None:
    md = generate_claude_md(_p(package_managers=["npm"]))
    assert "npm install" in md
