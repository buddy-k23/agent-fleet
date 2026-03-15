"""Tests for background task worker."""

import time
from unittest.mock import MagicMock

from agent_fleet.core.state import FleetState
from agent_fleet.core.worker import TaskWorker


class TestTaskWorker:
    def test_submit_task(self) -> None:
        worker = TaskWorker()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"status": "completed", "total_tokens": 100}

        state: FleetState = {
            "task_id": "w1",
            "repo": "/r",
            "description": "Test",
            "workflow_name": "default",
            "status": "running",
        }
        worker.submit("w1", state, mock_graph)
        # Give thread time to start
        time.sleep(0.1)
        assert worker.is_running("w1") or worker.get_result("w1") is not None
        worker.shutdown()

    def test_get_result_after_completion(self) -> None:
        worker = TaskWorker()
        mock_graph = MagicMock()
        final = {"status": "completed", "total_tokens": 500}
        mock_graph.invoke.return_value = final

        state: FleetState = {
            "task_id": "w2",
            "repo": "/r",
            "description": "Test",
            "workflow_name": "default",
            "status": "running",
        }
        worker.submit("w2", state, mock_graph)
        # Wait for completion
        time.sleep(0.5)
        result = worker.get_result("w2")
        assert result is not None
        assert result["status"] == "completed"
        worker.shutdown()

    def test_is_running_false_for_unknown_task(self) -> None:
        worker = TaskWorker()
        assert worker.is_running("unknown") is False
        worker.shutdown()

    def test_get_result_none_for_unknown_task(self) -> None:
        worker = TaskWorker()
        assert worker.get_result("unknown") is None
        worker.shutdown()

    def test_handles_graph_error(self) -> None:
        worker = TaskWorker()
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = RuntimeError("graph crashed")

        state: FleetState = {
            "task_id": "w3",
            "repo": "/r",
            "description": "Test",
            "workflow_name": "default",
            "status": "running",
        }
        worker.submit("w3", state, mock_graph)
        time.sleep(0.5)
        result = worker.get_result("w3")
        assert result is not None
        assert result["status"] == "error"
        worker.shutdown()
