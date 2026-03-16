"""Agent Fleet CLI — command-line interface."""

import subprocess
import uuid
from pathlib import Path

import typer

from agent_fleet import __version__
from agent_fleet.agents.registry import AgentRegistry
from agent_fleet.core.orchestrator import FleetOrchestrator
from agent_fleet.core.state import FleetState
from agent_fleet.workspace.worktree import WorktreeManager

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
    repo_path = Path(repo).resolve()
    if not repo_path.exists():
        typer.echo(f"Error: repo path does not exist: {repo_path}")
        raise typer.Exit(1)

    workflow_path = CONFIG_DIR / "workflows" / f"{workflow}.yaml"
    if not workflow_path.exists():
        typer.echo(f"Error: workflow not found: {workflow_path}")
        raise typer.Exit(1)

    task_id = uuid.uuid4().hex[:8]
    task_branch = f"fleet/task-{task_id}"

    typer.echo(f"Agent Fleet — Running task {task_id}")
    typer.echo(f"  Repo:     {repo_path}")
    typer.echo(f"  Task:     {task}")
    typer.echo(f"  Workflow: {workflow}")
    typer.echo(f"  Branch:   {task_branch}")
    typer.echo()

    # Create task branch
    result = subprocess.run(
        ["git", "branch", task_branch],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "already exists" not in result.stderr:
        typer.echo(f"Error creating task branch: {result.stderr}")
        raise typer.Exit(1)

    # Build orchestrator
    orch = FleetOrchestrator(
        workflow_path=workflow_path,
        agents_dir=CONFIG_DIR / "agents",
        repo_path=repo_path,
    )

    # Build initial state
    state: FleetState = {
        "task_id": task_id,
        "repo": str(repo_path),
        "description": task,
        "workflow_name": workflow,
        "status": "running",
        "current_stage": None,
        "completed_stages": [],
        "retry_counts": {},
        "stage_outputs": {},
        "stage_errors": {},
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "pr_url": None,
        "error_message": None,
    }

    # Run the orchestrator graph
    graph = orch.build_graph()
    typer.echo("Starting pipeline...")
    typer.echo()

    final_state: FleetState = {}
    try:
        final_state = graph.invoke(state)
    finally:
        # Clean up worktrees regardless of success or failure
        try:
            worktree_mgr = WorktreeManager(repo_path)
            worktree_mgr.cleanup_all(task_id)
            typer.echo("Worktrees cleaned up.")
        except Exception:
            pass  # Best-effort cleanup

    # Print results
    typer.echo()
    typer.echo("=" * 60)
    if final_state.get("status") == "completed":
        typer.echo("Pipeline COMPLETED successfully!")
    else:
        typer.echo(f"Pipeline ended with status: {final_state.get('status')}")
        if final_state.get("error_message"):
            typer.echo(f"Error: {final_state['error_message']}")

    typer.echo(f"  Stages completed: {final_state.get('completed_stages', [])}")
    typer.echo(f"  Total tokens:     {final_state.get('total_tokens', 0)}")
    typer.echo(f"  Task branch:      {task_branch}")
    typer.echo("=" * 60)


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


@app.command()
def init(
    repo: str = typer.Option(..., help="Path to the git repository"),
    dry_run: bool = typer.Option(True, help="Display only, don't save"),
) -> None:
    """Onboard a project — scan codebase and recommend agents + workflow."""
    from agent_fleet.onboarding.recommender import recommend_agents, recommend_workflow
    from agent_fleet.onboarding.scanner import scan_project

    repo_path = Path(repo).resolve()
    if not repo_path.exists():
        typer.echo(f"Error: path does not exist: {repo_path}")
        raise typer.Exit(1)

    typer.echo(f"🔍 Scanning {repo_path}...\n")
    profile = scan_project(repo_path)

    typer.echo(f"  Languages:  {', '.join(profile.languages) or 'none'}")
    typer.echo(f"  Frameworks: {', '.join(profile.frameworks) or 'none'}")
    typer.echo(f"  Tests:      {', '.join(profile.test_frameworks) or 'none'}")
    typer.echo(f"  Database:   {', '.join(profile.databases) or 'none'}")
    typer.echo(f"  CI:         {profile.ci_platform or 'none'}")
    typer.echo(f"  CLAUDE.md:  {'Found ✓' if profile.has_claude_md else 'Not found'}")
    typer.echo(f"  LOC:        ~{profile.estimated_loc:,}")

    agents = recommend_agents(profile)
    typer.echo(f"\n🤖 Recommended agents: ({len(agents)})")
    for a in agents:
        typer.echo(f"  {a['name']:18s} {a['model']}")

    wf = recommend_workflow(profile)
    stage_names = [s["name"] for s in wf["stages"]]
    typer.echo(f"\n📋 Recommended workflow: {wf['name']}")
    typer.echo(f"  {' → '.join(stage_names)}")

    if dry_run:
        typer.echo("\n(dry run — use --no-dry-run to save)")
    else:
        typer.echo("\n✅ Saving not yet implemented (use --dry-run)")
    typer.echo()


if __name__ == "__main__":
    app()
