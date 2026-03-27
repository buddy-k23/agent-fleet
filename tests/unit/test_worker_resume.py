"""Tests for worker checkpoint resume logic."""

from unittest.mock import MagicMock, patch

import pytest

from agent_fleet.worker import FleetWorker


@pytest.fixture
def mock_service_client():
    return MagicMock()


@pytest.fixture
def worker(mock_service_client):
    with patch("agent_fleet.worker.get_service_client", return_value=mock_service_client), \
         patch("agent_fleet.worker.get_checkpointer") as mock_cp:
        mock_cp.return_value = MagicMock()
        w = FleetWorker(max_concurrent_tasks=2, poll_interval_seconds=0.1)
        yield w
        w.shutdown()


class TestResumeLogic:
    def _make_task(self, status="queued"):
        return {
            "id": "task-resume", "repo": "/tmp/repo", "description": "Do something",
            "workflow_id": "wf-1", "user_id": "user-1", "status": status,
        }

    def test_fresh_task_invokes_with_initial_state(self, worker):
        """Queued task calls graph.invoke(initial_state, config)."""
        task = self._make_task(status="queued")
        worker._workflows_repo.get = MagicMock(return_value={
            "name": "wf", "stages": [{"name": "plan", "agent": "Arch"}],
        })
        worker._agents_repo.list_by_user = MagicMock(return_value=[])
        worker._tasks_repo.update_status = MagicMock()
        worker._events_repo.append = MagicMock()

        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"status": "completed", "completed_stages": ["plan"]}
        mock_writer = MagicMock()
        mock_writer.build_graph.return_value = mock_graph

        with patch("agent_fleet.worker.OrchestratorFactory") as mock_factory, \
             patch("agent_fleet.worker.WorktreeManager"):
            mock_factory.from_supabase.return_value = mock_writer
            worker._execute_task(task)

        call_args = mock_graph.invoke.call_args
        assert call_args[0][0] is not None  # initial_state dict
        assert call_args[0][0]["task_id"] == "task-resume"

    def test_resuming_task_checks_checkpoint(self, worker):
        """Resuming task calls graph.get_state() and resumes if checkpoint exists."""
        task = self._make_task(status="resuming")
        worker._workflows_repo.get = MagicMock(return_value={
            "name": "wf", "stages": [{"name": "plan", "agent": "Arch"}],
        })
        worker._agents_repo.list_by_user = MagicMock(return_value=[])
        worker._tasks_repo.update_status = MagicMock()
        worker._events_repo.append = MagicMock()

        mock_state = MagicMock()
        mock_state.values = {"task_id": "task-resume", "current_stage": "plan"}
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = mock_state
        mock_graph.invoke.return_value = {"status": "completed"}
        mock_writer = MagicMock()
        mock_writer.build_graph.return_value = mock_graph

        with patch("agent_fleet.worker.OrchestratorFactory") as mock_factory, \
             patch("agent_fleet.worker.WorktreeManager"):
            mock_factory.from_supabase.return_value = mock_writer
            worker._execute_task(task)

        mock_graph.get_state.assert_called_once()
        call_args = mock_graph.invoke.call_args
        assert call_args[0][0] is None  # resume from checkpoint

    def test_resuming_no_checkpoint_falls_back_to_fresh(self, worker):
        """Resuming task with no checkpoint starts fresh."""
        task = self._make_task(status="resuming")
        worker._workflows_repo.get = MagicMock(return_value={
            "name": "wf", "stages": [{"name": "plan", "agent": "Arch"}],
        })
        worker._agents_repo.list_by_user = MagicMock(return_value=[])
        worker._tasks_repo.update_status = MagicMock()
        worker._events_repo.append = MagicMock()

        mock_state = MagicMock()
        mock_state.values = {}  # Empty — no checkpoint
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = mock_state
        mock_graph.invoke.return_value = {"status": "completed"}
        mock_writer = MagicMock()
        mock_writer.build_graph.return_value = mock_graph

        with patch("agent_fleet.worker.OrchestratorFactory") as mock_factory, \
             patch("agent_fleet.worker.WorktreeManager"):
            mock_factory.from_supabase.return_value = mock_writer
            worker._execute_task(task)

        call_args = mock_graph.invoke.call_args
        assert call_args[0][0] is not None  # fresh start
        assert call_args[0][0]["task_id"] == "task-resume"


class TestCheckpointCleanup:
    def _make_task(self, status="queued"):
        return {
            "id": "task-done", "repo": "/tmp/repo", "description": "x",
            "workflow_id": "wf-1", "user_id": "u-1", "status": status,
        }

    def test_checkpoint_cleaned_after_completion(self, worker):
        """Checkpoint is deleted after task completes successfully."""
        task = self._make_task()
        worker._workflows_repo.get = MagicMock(return_value={
            "name": "wf", "stages": [{"name": "plan", "agent": "Arch"}],
        })
        worker._agents_repo.list_by_user = MagicMock(return_value=[])
        worker._tasks_repo.update_status = MagicMock()
        worker._events_repo.append = MagicMock()

        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"status": "completed"}
        mock_writer = MagicMock()
        mock_writer.build_graph.return_value = mock_graph

        with patch("agent_fleet.worker.OrchestratorFactory") as mock_factory, \
             patch("agent_fleet.worker.WorktreeManager"):
            mock_factory.from_supabase.return_value = mock_writer
            worker._execute_task(task)

        worker._checkpointer.delete_thread.assert_called_once()

    def test_checkpoint_not_cleaned_on_error(self, worker):
        """Checkpoint is preserved when task errors (for future resume)."""
        task = self._make_task()
        worker._workflows_repo.get = MagicMock(return_value=None)  # Will cause error
        worker._tasks_repo.update_status = MagicMock()
        worker._events_repo.append = MagicMock()

        with patch("agent_fleet.worker.WorktreeManager"):
            worker._execute_task(task)

        worker._checkpointer.delete_thread.assert_not_called()

    def test_checkpoint_cleanup_failure_is_non_fatal(self, worker):
        """If checkpoint cleanup fails, task still completes normally."""
        task = self._make_task()
        worker._workflows_repo.get = MagicMock(return_value={
            "name": "wf", "stages": [{"name": "plan", "agent": "Arch"}],
        })
        worker._agents_repo.list_by_user = MagicMock(return_value=[])
        worker._tasks_repo.update_status = MagicMock()
        worker._events_repo.append = MagicMock()

        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"status": "completed"}
        mock_writer = MagicMock()
        mock_writer.build_graph.return_value = mock_graph
        worker._checkpointer.delete_thread.side_effect = RuntimeError("DB gone")

        with patch("agent_fleet.worker.OrchestratorFactory") as mock_factory, \
             patch("agent_fleet.worker.WorktreeManager"):
            mock_factory.from_supabase.return_value = mock_writer
            worker._execute_task(task)

        # Task should still be marked completed
        worker._tasks_repo.update_status.assert_called()


class TestStaleRecoveryStatus:
    def test_stale_tasks_set_to_resuming(self, worker):
        """Stale tasks are set to 'resuming', not 'queued'."""
        stale_tasks = [{"id": "task-old", "started_at": "2026-03-22T00:00:00+00:00"}]
        worker._tasks_repo.list_by_status = MagicMock(return_value=stale_tasks)
        worker._tasks_repo.update_status = MagicMock()
        worker._recover_stale_tasks()
        worker._tasks_repo.update_status.assert_called_with("task-old", "resuming")
