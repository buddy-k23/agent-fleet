"""Background task worker — runs pipeline in a thread."""

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

import structlog

from agent_fleet.core.state import FleetState

logger = structlog.get_logger()


class TaskWorker:
    """Manages background pipeline executions via thread pool."""

    def __init__(self, max_workers: int = 5) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: dict[str, Future] = {}  # type: ignore[type-arg]
        self._results: dict[str, FleetState] = {}

    def submit(self, task_id: str, state: FleetState, graph: Any) -> None:
        """Submit a pipeline for background execution."""
        logger.info("worker_submit", task_id=task_id)
        future = self._executor.submit(self._run, task_id, state, graph)
        self._futures[task_id] = future

    def is_running(self, task_id: str) -> bool:
        """Check if a task is currently running."""
        future = self._futures.get(task_id)
        if future is None:
            return False
        return not future.done()

    def get_result(self, task_id: str) -> FleetState | None:
        """Get the result of a completed task. Returns None if not done or unknown."""
        if task_id in self._results:
            return self._results[task_id]
        future = self._futures.get(task_id)
        if future is not None and future.done():
            try:
                self._results[task_id] = future.result()
            except Exception:
                pass
            return self._results.get(task_id)
        return None

    def shutdown(self) -> None:
        """Shut down the thread pool."""
        self._executor.shutdown(wait=False)

    def _run(self, task_id: str, state: FleetState, graph: Any) -> FleetState:
        """Execute the pipeline graph in a background thread."""
        try:
            logger.info("worker_start", task_id=task_id)
            result = graph.invoke(state)
            logger.info(
                "worker_complete",
                task_id=task_id,
                status=result.get("status"),
            )
            self._results[task_id] = result
            return result
        except Exception as e:
            logger.error("worker_error", task_id=task_id, error=str(e))
            error_state: FleetState = {
                **state,
                "status": "error",
                "error_message": f"Worker error: {e}",
            }
            self._results[task_id] = error_state
            return error_state
