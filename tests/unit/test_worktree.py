"""Tests for git worktree manager."""

import subprocess
from pathlib import Path

import pytest

from agent_fleet.workspace.worktree import WorktreeManager


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with an initial commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    (tmp_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    return tmp_path


class TestWorktreeCreate:
    def test_creates_worktree_directory(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        wt_path = mgr.create(task_id="task-001", stage="backend")
        assert wt_path.exists()
        assert wt_path.is_dir()

    def test_worktree_contains_repo_files(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        wt_path = mgr.create(task_id="task-002", stage="plan")
        assert (wt_path / "README.md").exists()

    def test_worktree_on_correct_branch(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        wt_path = mgr.create(task_id="task-003", stage="frontend")
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=wt_path, capture_output=True, text=True,
        )
        assert "fleet/task-003/frontend" in result.stdout.strip()

    def test_worktree_path_uses_naming_convention(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        wt_path = mgr.create(task_id="task-004", stage="review")
        assert "fleet-worktree-task-004-review" in wt_path.name


class TestWorktreeCleanup:
    def test_cleanup_removes_worktree(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        wt_path = mgr.create(task_id="task-005", stage="plan")
        assert wt_path.exists()
        mgr.cleanup(wt_path)
        assert not wt_path.exists()

    def test_cleanup_all_removes_task_worktrees(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        wt1 = mgr.create(task_id="task-006", stage="backend")
        wt2 = mgr.create(task_id="task-006", stage="frontend")
        assert wt1.exists()
        assert wt2.exists()
        mgr.cleanup_all("task-006")
        assert not wt1.exists()
        assert not wt2.exists()

    def test_cleanup_all_leaves_other_tasks(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        wt_keep = mgr.create(task_id="task-007", stage="plan")
        wt_remove = mgr.create(task_id="task-008", stage="plan")
        mgr.cleanup_all("task-008")
        assert wt_keep.exists()
        assert not wt_remove.exists()
        mgr.cleanup(wt_keep)


class TestWorktreeList:
    def test_list_worktrees(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        mgr.create(task_id="task-009", stage="a")
        mgr.create(task_id="task-009", stage="b")
        worktrees = mgr.list_worktrees()
        assert len(worktrees) >= 2

    def test_list_excludes_main_repo(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        mgr.create(task_id="task-010", stage="plan")
        worktrees = mgr.list_worktrees()
        assert git_repo not in worktrees
        mgr.cleanup_all("task-010")

    def test_list_empty_when_no_worktrees(self, git_repo: Path) -> None:
        mgr = WorktreeManager(git_repo)
        worktrees = mgr.list_worktrees()
        assert len(worktrees) == 0
