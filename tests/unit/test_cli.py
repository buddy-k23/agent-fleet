"""Tests for Typer CLI."""

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Agent Fleet" in result.stdout


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_agents_list() -> None:
    result = runner.invoke(app, ["agents", "list"])
    assert result.exit_code == 0
    assert "architect" in result.stdout.lower()
    assert "backend" in result.stdout.lower()


def test_agents_list_shows_all_six() -> None:
    result = runner.invoke(app, ["agents", "list"])
    assert result.exit_code == 0
    for agent in ["architect", "backend-dev", "frontend-dev", "reviewer", "tester", "integrator"]:
        assert agent in result.stdout.lower()


def test_run_nonexistent_repo_exits_1() -> None:
    result = runner.invoke(app, ["run", "--repo", "/nonexistent/path", "--task", "Test"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_run_nonexistent_workflow_exits_1(tmp_path) -> None:  # type: ignore[no-untyped-def]
    result = runner.invoke(
        app, ["run", "--repo", str(tmp_path), "--task", "Test", "--workflow", "nope"]
    )
    assert result.exit_code == 1
    assert "not found" in result.stdout


def test_status_shows_stub() -> None:
    result = runner.invoke(app, ["status", "task-001"])
    assert result.exit_code == 0
