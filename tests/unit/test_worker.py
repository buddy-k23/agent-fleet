"""Tests for the fleet-worker process — poll loop, pickup, concurrency, shutdown."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from agent_fleet.worker import FleetWorker


@pytest.fixture
def mock_service_client():
    return MagicMock()


@pytest.fixture
def worker(mock_service_client):
    with patch("agent_fleet.worker.get_service_client", return_value=mock_service_client):
        w = FleetWorker(
            max_concurrent_tasks=2,
            poll_interval_seconds=0.1,
        )
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
        chain.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
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
        chain.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
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

        worker._tasks_repo.update_status.assert_called_with("task-old", "queued")

    def test_does_not_requeue_recently_started_tasks(self, worker):
        """Tasks started less than 30 min ago are NOT re-queued."""
        recent_task = [
            {"id": "task-recent", "started_at": datetime.now(UTC).isoformat()},
        ]
        worker._tasks_repo.list_by_status = MagicMock(return_value=recent_task)
        worker._tasks_repo.update_status = MagicMock()

        worker._recover_stale_tasks()

        worker._tasks_repo.update_status.assert_not_called()
