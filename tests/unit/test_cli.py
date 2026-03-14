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


def test_run_shows_stub() -> None:
    result = runner.invoke(app, ["run", "--repo", "/tmp/repo", "--task", "Test task"])
    assert result.exit_code == 0
    assert "Submitting" in result.stdout


def test_status_shows_stub() -> None:
    result = runner.invoke(app, ["status", "task-001"])
    assert result.exit_code == 0
