"""Git worktree management for agent isolation."""

import shutil
import subprocess
from pathlib import Path

import structlog

from agent_fleet.exceptions import WorktreeError

logger = structlog.get_logger()


class WorktreeManager:
    """Manages git worktrees for agent task isolation.

    Each agent gets its own worktree so agents never modify
    the main working tree. Worktrees are cleaned up in finally
    blocks to prevent disk accumulation.
    """

    def __init__(self, repo_root: Path) -> None:
        self._repo = repo_root
        self._worktrees_dir = repo_root / ".fleet-worktrees"
        self._worktrees_dir.mkdir(exist_ok=True)

    def create(self, task_id: str, stage: str, base_branch: str | None = None) -> Path:
        """Create a new worktree for a task stage.

        Returns the path to the new worktree directory.
        Branch name: fleet/{task_id}/{stage}
        Worktree dir: .fleet-worktrees/fleet-worktree-{task_id}-{stage}

        If base_branch is provided, the stage branch is created from that branch
        instead of HEAD. Used to branch off the task branch (fleet/task-{id}).
        """
        branch_name = f"fleet/{task_id}-{stage}"
        worktree_name = f"fleet-worktree-{task_id}-{stage}"
        worktree_path = self._worktrees_dir / worktree_name

        try:
            if base_branch:
                self._run_git("branch", branch_name, base_branch)
            else:
                self._run_git("branch", branch_name)
        except WorktreeError:
            pass  # Branch may already exist

        try:
            self._run_git("worktree", "add", str(worktree_path), branch_name)
        except WorktreeError as e:
            raise WorktreeError(f"Failed to create worktree: {e}") from e

        logger.info(
            "worktree_created",
            task_id=task_id,
            stage=stage,
            path=str(worktree_path),
            branch=branch_name,
        )
        return worktree_path

    def cleanup(self, worktree_path: Path) -> None:
        """Remove a worktree. Falls back to manual cleanup if git fails."""
        try:
            self._run_git("worktree", "remove", str(worktree_path), "--force")
        except WorktreeError:
            if worktree_path.exists():
                shutil.rmtree(worktree_path)
            self._run_git("worktree", "prune")

        logger.info("worktree_cleaned", path=str(worktree_path))

    def cleanup_all(self, task_id: str) -> None:
        """Remove all worktrees for a given task."""
        prefix = f"fleet-worktree-{task_id}"
        for wt in self.list_worktrees():
            if wt.name.startswith(prefix):
                self.cleanup(wt)

    def list_worktrees(self) -> list[Path]:
        """List all active worktrees (excluding the main repo)."""
        result = self._run_git("worktree", "list", "--porcelain")
        paths: list[Path] = []
        for line in result.splitlines():
            if line.startswith("worktree "):
                p = Path(line.split(" ", 1)[1])
                if p != self._repo:
                    paths.append(p)
        return paths

    def _run_git(self, *args: str) -> str:
        """Run a git command in the repo directory."""
        result = subprocess.run(
            ["git", *args],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout
