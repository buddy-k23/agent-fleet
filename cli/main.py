"""Agent Fleet CLI — command-line interface."""

from pathlib import Path

import typer

from agent_fleet import __version__
from agent_fleet.agents.registry import AgentRegistry

app = typer.Typer(name="fleet", help="Agent Fleet — Multi-model AI agent orchestration")
agents_app = typer.Typer(help="Manage agents")
app.add_typer(agents_app, name="agents")

# Default config directory (relative to project root)
CONFIG_DIR = Path(__file__).parent.parent / "config"


@app.command()
def version() -> None:
    """Show version."""
    typer.echo(f"Agent Fleet v{__version__}")


@app.command()
def run(
    repo: str = typer.Option(..., help="Path to the git repository"),
    task: str = typer.Option(..., help="Task description"),
    workflow: str = typer.Option("default", help="Workflow name"),
) -> None:
    """Submit a task to the agent fleet."""
    typer.echo("Submitting task to fleet...")
    typer.echo(f"  Repo: {repo}")
    typer.echo(f"  Task: {task}")
    typer.echo(f"  Workflow: {workflow}")
    typer.echo("Task submission not yet implemented — API integration coming next.")


@agents_app.command("list")
def agents_list() -> None:
    """List available agents."""
    agents_dir = CONFIG_DIR / "agents"
    if not agents_dir.exists():
        typer.echo("No agents directory found.")
        raise typer.Exit(1)
    registry = AgentRegistry(agents_dir)
    for name in registry.list_agents():
        config = registry.get(name)
        typer.echo(f"  {name:20s} {config.description[:60]}")


@app.command()
def status(task_id: str = typer.Argument(..., help="Task ID")) -> None:
    """Check task status."""
    typer.echo(f"Checking status for {task_id}...")
    typer.echo("Status check not yet implemented.")


if __name__ == "__main__":
    app()
