"""Fleet Worker — polls Supabase for queued tasks and executes them."""

import signal
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime

import structlog

from agent_fleet.api.deps import get_service_client
from agent_fleet.store.supabase_repo import (
    SupabaseAgentRepository,
    SupabaseEventRepository,
    SupabaseExecutionRepository,
    SupabaseGateResultRepository,
    SupabaseTaskRepository,
    SupabaseWorkflowRepository,
)
from agent_fleet.worker.checkpointer import get_checkpointer  # noqa: F401
from agent_fleet.worker.orchestrator_factory import OrchestratorFactory

logger = structlog.get_logger()


class FleetWorker:
    """Polls Supabase for queued tasks and runs them through the orchestrator."""

    def __init__(
        self,
        max_concurrent_tasks: int = 3,
        poll_interval_seconds: float = 3.0,
    ) -> None:
        self._max_concurrent = max_concurrent_tasks
        self._poll_interval = poll_interval_seconds
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks + 2)
        self._active_futures: dict[str, Future] = {}

        client = get_service_client()
        self._client = client
        self._tasks_repo = SupabaseTaskRepository(client)
        self._executions_repo = SupabaseExecutionRepository(client)
        self._gate_results_repo = SupabaseGateResultRepository(client)
        self._events_repo = SupabaseEventRepository(client)
        self._workflows_repo = SupabaseWorkflowRepository(client)
        self._agents_repo = SupabaseAgentRepository(client)

    def start(self) -> None:
        """Start the poll loop. Blocks until shutdown."""
        self._running = True
        logger.info(
            "worker_starting",
            max_concurrent=self._max_concurrent,
            poll_interval=self._poll_interval,
        )

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        self._recover_stale_tasks()

        while self._running:
            try:
                self._cleanup_finished_futures()
                self._poll_once()
                self._write_heartbeat()
            except Exception as e:
                logger.error("poll_error", error=str(e))
            time.sleep(self._poll_interval)

        logger.info("worker_stopped")

    def _write_heartbeat(self) -> None:
        """Write heartbeat timestamp for health checks."""
        import json

        try:
            with open("/tmp/fleet-worker-heartbeat", "w") as f:
                json.dump({"timestamp": datetime.now(UTC).isoformat()}, f)
        except OSError:
            pass

    def _handle_signal(self, signum: int, frame: object) -> None:
        """Handle SIGINT/SIGTERM for graceful shutdown."""
        logger.info("shutdown_signal_received", signal=signum)
        self.shutdown()

    def shutdown(self, timeout: float = 300.0) -> None:
        """Gracefully shut down: wait for in-flight tasks, re-queue the rest."""
        self._running = False

        for task_id, future in list(self._active_futures.items()):
            if not future.done():
                logger.info("waiting_for_task", task_id=task_id)
                try:
                    future.result(timeout=timeout)
                except Exception:
                    pass

            if not future.done():
                logger.warning("requeuing_task", task_id=task_id)
                try:
                    self._tasks_repo.update_status(task_id, "queued")
                except Exception as e:
                    logger.error("requeue_failed", task_id=task_id, error=str(e))

        self._executor.shutdown(wait=False)

    def _poll_once(self) -> None:
        """Single poll iteration: fetch queued tasks and start them."""
        active_count = len(self._active_futures)
        if active_count >= self._max_concurrent:
            return

        tasks = self._fetch_queued_tasks(limit=self._max_concurrent - active_count)
        for task in tasks:
            task_id = task["id"]

            if not self._tasks_repo.atomic_pickup(task_id):
                logger.debug("pickup_lost", task_id=task_id)
                continue

            logger.info("task_picked_up", task_id=task_id)
            future = self._executor.submit(self._execute_task, task)
            self._active_futures[task_id] = future

    def _fetch_queued_tasks(self, limit: int = 5) -> list[dict]:
        """Fetch queued tasks from Supabase, ordered by created_at."""
        result = (
            self._client.table("tasks")
            .select("*")
            .in_("status", ["queued", "resuming"])
            .order("created_at")
            .limit(limit)
            .execute()
        )
        return result.data

    def _execute_task(self, task: dict) -> None:
        """Execute a single task through the orchestrator pipeline."""
        task_id = task["id"]
        logger.info("task_executing", task_id=task_id)

        try:
            workflow_data = self._workflows_repo.get(task["workflow_id"])
            if not workflow_data:
                raise ValueError(f"Workflow {task['workflow_id']} not found")

            agent_configs = self._agents_repo.list_by_user(task["user_id"])

            repos = {
                "tasks": self._tasks_repo,
                "executions": self._executions_repo,
                "gate_results": self._gate_results_repo,
                "events": self._events_repo,
            }

            orchestrator = OrchestratorFactory.from_supabase(
                workflow_data=workflow_data,
                agent_configs=agent_configs,
                task_id=task_id,
                repos=repos,
            )

            graph = orchestrator.build_graph()
            initial_state = {
                "task_id": task_id,
                "repo": task["repo"],
                "description": task["description"],
                "workflow_name": workflow_data.get("name", "unknown"),
                "status": "running",
                "completed_stages": [],
                "stage_outputs": {},
                "total_tokens": 0,
                "total_cost_usd": 0.0,
            }

            result = graph.invoke(initial_state)

            final_status = result.get("status", "completed")
            self._tasks_repo.update_status(
                task_id,
                final_status,
                completed_stages=result.get("completed_stages", []),
                total_tokens=result.get("total_tokens", 0),
                total_cost_usd=result.get("total_cost_usd", 0.0),
                pr_url=result.get("pr_url"),
            )
            logger.info("task_completed", task_id=task_id, status=final_status)

        except Exception as e:
            logger.error("task_failed", task_id=task_id, error=str(e))
            try:
                self._tasks_repo.update_status(task_id, "error", error_message=str(e)[:1000])
                self._events_repo.append(task_id, "task_error", {"error": str(e)})
            except Exception as write_err:
                logger.error("status_write_failed", task_id=task_id, error=str(write_err))

        finally:
            try:
                from pathlib import Path

                from agent_fleet.workspace.worktree import WorktreeManager

                repo_path = task.get("repo")
                if repo_path:
                    wt_manager = WorktreeManager(Path(repo_path))
                    wt_manager.cleanup_all(task_id)
                    logger.info("worktrees_cleaned", task_id=task_id)
            except Exception as cleanup_err:
                logger.error("worktree_cleanup_failed", task_id=task_id, error=str(cleanup_err))

    def _cleanup_finished_futures(self) -> None:
        """Remove completed futures from the active set."""
        done = [tid for tid, f in self._active_futures.items() if f.done()]
        for tid in done:
            future = self._active_futures.pop(tid)
            exc = future.exception()
            if exc:
                logger.error("future_exception", task_id=tid, error=str(exc))

    def _recover_stale_tasks(self, stale_threshold_minutes: int = 30) -> None:
        """On startup, re-queue tasks stuck in 'running' past timeout."""
        running_tasks = self._tasks_repo.list_by_status("running")
        now = datetime.now(UTC)

        for task in running_tasks:
            started_at = task.get("started_at")
            if not started_at:
                logger.warning("recovering_stale_task", task_id=task["id"], reason="no started_at")
                self._tasks_repo.update_status(task["id"], "resuming")
                continue

            if isinstance(started_at, str):
                started_at = datetime.fromisoformat(started_at)

            age_minutes = (now - started_at).total_seconds() / 60
            if age_minutes > stale_threshold_minutes:
                logger.warning(
                    "recovering_stale_task",
                    task_id=task["id"],
                    age_minutes=round(age_minutes),
                )
                self._tasks_repo.update_status(task["id"], "resuming")
