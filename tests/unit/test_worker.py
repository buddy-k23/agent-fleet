"""Tests for the fleet-worker process — poll loop, pickup, concurrency, shutdown."""

from concurrent.futures import Future
from datetime import UTC, datetime
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


class TestPollLoop:
    def test_picks_up_queued_task(self, worker, mock_service_client):
        """Worker picks up a queued task and starts it."""
        task_row = {
            "id": "task-1",
            "repo": "/tmp/repo",
            "description": "Fix bug",
            "workflow_id": "wf-1",
            "user_id": "user-1",
        }
        chain = mock_service_client.table.return_value.select.return_value
        chain.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            task_row
        ]

        worker._tasks_repo.atomic_pickup = MagicMock(return_value=True)
        worker._tasks_repo.update_status = MagicMock()

        with patch.object(worker._executor, "submit", wraps=worker._executor.submit) as mock_submit:
            worker._poll_once()

        worker._tasks_repo.atomic_pickup.assert_called_once_with("task-1")
        mock_submit.assert_called_once()  # task was submitted to executor
        assert "task-1" in worker._active_futures  # future tracked

    def test_skips_task_if_atomic_pickup_fails(self, worker, mock_service_client):
        """Worker skips task if another worker grabbed it first."""
        task_row = {
            "id": "task-1",
            "repo": "/tmp/repo",
            "description": "Fix bug",
            "workflow_id": "wf-1",
            "user_id": "user-1",
        }
        chain = mock_service_client.table.return_value.select.return_value
        chain.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            task_row
        ]

        worker._tasks_repo.atomic_pickup = MagicMock(return_value=False)

        worker._poll_once()

        assert "task-1" not in worker._active_futures

    def test_respects_max_concurrent_tasks(self, worker):
        """Worker skips pickup when at capacity."""
        worker._active_futures = {"task-1": MagicMock(), "task-2": MagicMock()}

        with patch.object(worker, "_fetch_queued_tasks") as mock_fetch:
            worker._poll_once()

        mock_fetch.assert_not_called()


class TestGracefulShutdown:
    def test_shutdown_sets_running_false(self, worker):
        """Shutdown signals the poll loop to stop."""
        worker._running = True
        worker.shutdown()
        assert worker._running is False


class TestStaleTaskRecovery:
    def test_recovers_stale_running_tasks_on_startup(self, worker):
        """On startup, re-queue tasks stuck in 'running' past timeout (30 min)."""
        stale_tasks = [
            {"id": "task-old", "started_at": "2026-03-22T00:00:00+00:00"},
        ]
        worker._tasks_repo.list_by_status = MagicMock(return_value=stale_tasks)
        worker._tasks_repo.update_status = MagicMock()

        worker._recover_stale_tasks()

        worker._tasks_repo.update_status.assert_called_with("task-old", "resuming")

    def test_does_not_requeue_recently_started_tasks(self, worker):
        """Tasks started less than 30 min ago are NOT re-queued."""
        recent_task = [
            {"id": "task-recent", "started_at": datetime.now(UTC).isoformat()},
        ]
        worker._tasks_repo.list_by_status = MagicMock(return_value=recent_task)
        worker._tasks_repo.update_status = MagicMock()

        worker._recover_stale_tasks()

        worker._tasks_repo.update_status.assert_not_called()

    def test_recover_stale_tasks_no_started_at(self, worker):
        """Task with no started_at field is immediately re-queued."""
        tasks = [{"id": "task-notime"}]  # no started_at key
        worker._tasks_repo.list_by_status = MagicMock(return_value=tasks)
        worker._tasks_repo.update_status = MagicMock()

        worker._recover_stale_tasks()

        worker._tasks_repo.update_status.assert_called_with("task-notime", "resuming")


class TestExecuteTask:
    def _make_task(self) -> dict:
        return {
            "id": "task-exec",
            "repo": "/tmp/repo",
            "description": "Do something",
            "workflow_id": "wf-1",
            "user_id": "user-1",
        }

    def test_execute_task_workflow_not_found(self, worker):
        """When workflow repo returns None, task status is set to error."""
        task = self._make_task()
        worker._workflows_repo.get = MagicMock(return_value=None)
        worker._tasks_repo.update_status = MagicMock()
        worker._events_repo.append = MagicMock()

        with patch("agent_fleet.worker.WorktreeManager"):
            worker._execute_task(task)

        worker._tasks_repo.update_status.assert_called_once()
        call_args = worker._tasks_repo.update_status.call_args
        assert call_args[0][0] == "task-exec"
        assert call_args[0][1] == "error"
        assert "wf-1" in call_args[1].get("error_message", "")

    def test_execute_task_graph_invoke_fails(self, worker):
        """When graph.invoke() raises, task status is set to error."""
        task = self._make_task()
        worker._workflows_repo.get = MagicMock(
            return_value={
                "name": "wf",
                "stages": [{"name": "plan", "agent": "Architect"}],
            }
        )
        worker._agents_repo.list_by_user = MagicMock(return_value=[])
        worker._tasks_repo.update_status = MagicMock()
        worker._events_repo.append = MagicMock()

        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = RuntimeError("graph exploded")

        mock_writer = MagicMock()
        mock_writer.build_graph.return_value = mock_graph

        with patch("agent_fleet.worker.OrchestratorFactory") as mock_factory:
            mock_factory.from_supabase.return_value = mock_writer
            with patch("agent_fleet.worker.WorktreeManager"):
                worker._execute_task(task)

        worker._tasks_repo.update_status.assert_called_once()
        call_args = worker._tasks_repo.update_status.call_args
        assert call_args[0][1] == "error"
        assert "graph exploded" in call_args[1].get("error_message", "")

    def test_execute_task_worktree_cleanup_on_error(self, worker):
        """Worktree cleanup runs in finally block even when execution fails."""
        task = self._make_task()
        worker._workflows_repo.get = MagicMock(return_value=None)
        worker._tasks_repo.update_status = MagicMock()
        worker._events_repo.append = MagicMock()

        mock_wt_instance = MagicMock()

        with patch("agent_fleet.worker.WorktreeManager", return_value=mock_wt_instance):
            worker._execute_task(task)

        mock_wt_instance.cleanup_all.assert_called_once_with("task-exec")


class TestCleanupFinishedFutures:
    def test_cleanup_removes_done_futures(self, worker):
        """Finished futures are removed from _active_futures; pending ones stay."""
        done_future: Future = Future()
        done_future.set_result(None)

        # Use a MagicMock future whose .done() returns False so _cleanup skips it.
        pending_mock: MagicMock = MagicMock(spec=Future)
        pending_mock.done.return_value = False

        worker._active_futures = {
            "task-done": done_future,
            "task-pending": pending_mock,
        }

        worker._cleanup_finished_futures()

        assert "task-done" not in worker._active_futures
        assert "task-pending" in worker._active_futures

        # Clear pending so teardown's shutdown() doesn't block
        worker._active_futures.clear()

    def test_cleanup_logs_exception_from_future(self, worker):
        """Futures that raised an exception have their errors logged."""
        failed_future: Future = Future()
        failed_future.set_exception(RuntimeError("something broke"))

        worker._active_futures = {"task-fail": failed_future}

        # Just ensure it doesn't raise and removes the future
        worker._cleanup_finished_futures()

        assert "task-fail" not in worker._active_futures


class TestPollOnceEdgeCases:
    def test_poll_once_with_no_queued_tasks(self, worker):
        """Empty task list from fetch results in no submissions."""
        worker._tasks_repo.atomic_pickup = MagicMock()

        with patch.object(worker, "_fetch_queued_tasks", return_value=[]):
            with patch.object(worker._executor, "submit") as mock_submit:
                worker._poll_once()

        mock_submit.assert_not_called()
        worker._tasks_repo.atomic_pickup.assert_not_called()
