"""Tests for CLAUDE.md generator."""

from agent_fleet.onboarding.claude_md_generator import generate_claude_md
from agent_fleet.onboarding.scanner import ProjectProfile


def _make_profile(**kwargs) -> ProjectProfile:  # type: ignore[no-untyped-def]
    defaults = {
        "name": "my-project",
        "repo_path": "/test",
        "languages": ["python"],
        "frameworks": ["fastapi"],
        "test_frameworks": ["pytest"],
        "databases": ["postgres"],
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


def test_generates_valid_markdown() -> None:
    md = generate_claude_md(_make_profile())
    assert "# my-project" in md
    assert "## Project Overview" in md
    assert "## Build & Test Commands" in md


def test_includes_stack() -> None:
    md = generate_claude_md(_make_profile(frameworks=["fastapi", "react"]))
    assert "fastapi" in md
    assert "react" in md


def test_includes_build_commands_for_pip() -> None:
    md = generate_claude_md(_make_profile(package_managers=["pip"]))
    assert "pip install" in md
    assert "pytest" in md


def test_includes_database() -> None:
    md = generate_claude_md(_make_profile(databases=["postgres"]))
    assert "postgres" in md


def test_includes_python_rules() -> None:
    md = generate_claude_md(_make_profile(languages=["python"]))
    assert "Type hints" in md


def test_includes_typescript_rules() -> None:
    md = generate_claude_md(_make_profile(languages=["typescript"], frameworks=["react"]))
    assert "data-testid" in md


def test_includes_commit_convention() -> None:
    md = generate_claude_md(_make_profile())
    assert "feat(scope)" in md
