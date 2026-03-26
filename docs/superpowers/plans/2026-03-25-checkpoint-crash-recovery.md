# Checkpoint Crash Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LangGraph Postgres-backed checkpointing so crashed tasks resume from their last completed node instead of restarting from scratch.

**Architecture:** A `PostgresSaver` checkpointer (from `langgraph-checkpoint-postgres`) connects to Supabase's Postgres. The worker passes it to `graph.compile()` and uses `task_id` as `thread_id`. On crash, stale tasks are set to `resuming` status; the worker checks for existing checkpoints and resumes if found. Checkpoints are deleted after task completion.

**Tech Stack:** langgraph-checkpoint-postgres, psycopg[binary], Supabase Postgres

**Spec:** `docs/superpowers/specs/2026-03-25-checkpoint-crash-recovery-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| **New** | |
| `src/agent_fleet/worker/checkpointer.py` | Factory function: creates `PostgresSaver` from `SUPABASE_DB_URL` |
| `tests/unit/test_checkpointer.py` | Tests for checkpointer factory |
| `tests/unit/test_worker_resume.py` | Tests for resume logic in `_execute_task` |
| **Modified** | |
| `src/agent_fleet/core/orchestrator.py:532-560` | `build_graph()` accepts optional `checkpointer` param |
| `src/agent_fleet/worker/__init__.py:30-45,108-136,138-211,221-243` | Resume logic, fetch both statuses, checkpoint cleanup, checkpointer init |
| `pyproject.toml:6-20` | Add `langgraph-checkpoint-postgres`, `psycopg[binary]` |
| `docker-compose.yml:34-40` | Add `SUPABASE_DB_URL` env var to worker |
| `src/agent_fleet/store/supabase_repo.py` | Update `atomic_pickup` to accept both `queued` and `resuming` statuses |
| `tests/unit/test_worker.py` | Update fixtures and assertions for checkpointer + resuming status |
| `CLAUDE.md` | Update principle #7 to reflect actual checkpoint implementation |

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml:6-20`

- [ ] **Step 1: Add checkpoint dependencies to pyproject.toml**

In the `dependencies` list, after `"langgraph>=0.4.0"` (line 10), add:

```python
    "langgraph-checkpoint-postgres>=2.0.0",
    "psycopg[binary]>=3.1.0",
```

- [ ] **Step 2: Install the new dependencies**

Run: `source .venv/bin/activate && pip install -e ".[dev]"`
Expected: Successfully installed langgraph-checkpoint-postgres and psycopg

- [ ] **Step 3: Verify import works**

Run: `python -c "from langgraph.checkpoint.postgres import PostgresSaver; print('OK')"`

If the import path is different (the package may use `langgraph_checkpoint_postgres`), adjust. Try:
```bash
python -c "import langgraph_checkpoint_postgres; print(dir(langgraph_checkpoint_postgres))"
```

Find the correct import path and note it for the next task.

- [ ] **Step 4: Verify PostgresSaver has a delete method**

Run: `python -c "from langgraph.checkpoint.postgres import PostgresSaver; print('delete' in dir(PostgresSaver))"`

If `False`, checkpoint cleanup will need an alternative approach (raw SQL or skipping cleanup). Note the result for Task 4.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "feat(worker): add langgraph-checkpoint-postgres dependency (#184)"
```

---

## Task 2: Create Checkpointer Factory

**Files:**
- Create: `src/agent_fleet/worker/checkpointer.py`
- Create: `tests/unit/test_checkpointer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_checkpointer.py
"""Tests for checkpointer factory — creates PostgresSaver from env vars."""

from unittest.mock import MagicMock, patch

import pytest

from agent_fleet.worker.checkpointer import get_checkpointer


def test_get_checkpointer_creates_saver_with_db_url():
    """Creates PostgresSaver using SUPABASE_DB_URL env var."""
    with patch.dict(
        "os.environ",
        {"SUPABASE_DB_URL": "postgresql://postgres:pass@db.example.com:5432/postgres"},
    ), patch("agent_fleet.worker.checkpointer.PostgresSaver") as mock_cls:
        mock_saver = MagicMock()
        mock_cls.from_conn_string.return_value = mock_saver

        result = get_checkpointer()

        mock_cls.from_conn_string.assert_called_once_with(
            "postgresql://postgres:pass@db.example.com:5432/postgres"
        )
        assert result is mock_saver


def test_get_checkpointer_raises_when_not_configured():
    """Raises RuntimeError if SUPABASE_DB_URL not set."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="SUPABASE_DB_URL"):
            get_checkpointer()


def test_get_checkpointer_calls_setup():
    """Calls setup() on the saver to create checkpoint tables."""
    with patch.dict(
        "os.environ",
        {"SUPABASE_DB_URL": "postgresql://postgres:pass@localhost:5432/postgres"},
    ), patch("agent_fleet.worker.checkpointer.PostgresSaver") as mock_cls:
        mock_saver = MagicMock()
        mock_cls.from_conn_string.return_value = mock_saver

        get_checkpointer()

        mock_saver.setup.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_checkpointer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_fleet.worker.checkpointer'`

- [ ] **Step 3: Implement checkpointer factory**

```python
# src/agent_fleet/worker/checkpointer.py
"""Checkpointer factory — creates PostgresSaver for LangGraph crash recovery."""

import os

import structlog

# Import path may vary by version — adjust based on Task 1 Step 3 findings
from langgraph.checkpoint.postgres import PostgresSaver

logger = structlog.get_logger()


def get_checkpointer() -> PostgresSaver:
    """Create a Postgres checkpointer using Supabase's direct DB connection.

    Requires SUPABASE_DB_URL env var (direct Postgres connection string,
    not the REST API URL). Available in Supabase dashboard under
    Project Settings > Database > Connection string.
    """
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError(
            "SUPABASE_DB_URL not configured: set to direct Postgres connection string "
            "(e.g., postgresql://postgres:password@db.xxx.supabase.co:5432/postgres)"
        )

    saver = PostgresSaver.from_conn_string(db_url)
    saver.setup()
    logger.info("checkpointer_ready", backend="postgres")
    return saver
```

**NOTE:** The import path `from langgraph.checkpoint.postgres import PostgresSaver` may differ depending on the installed package version. If the import fails, check:
- `from langgraph_checkpoint_postgres import PostgresSaver`
- `from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver` (if async needed)

Adjust the import in both the source and test files to match what's actually installed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_checkpointer.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_fleet/worker/checkpointer.py tests/unit/test_checkpointer.py
git commit -m "feat(worker): add checkpointer factory for PostgresSaver (#184)"
```

---

## Task 3: Update `build_graph()` to Accept Checkpointer

**Files:**
- Modify: `src/agent_fleet/core/orchestrator.py:532-560`
- Modify: `tests/unit/test_orchestrator.py` (add test)

- [ ] **Step 1: Write failing test**

Add to `tests/unit/test_orchestrator.py`:

```python
def test_build_graph_passes_checkpointer():
    """build_graph(checkpointer=X) passes X to graph.compile()."""
    from unittest.mock import MagicMock, patch

    from agent_fleet.agents.registry import AgentRegistry
    from agent_fleet.core.orchestrator import FleetOrchestrator
    from agent_fleet.core.workflow import GateConfig, StageConfig, WorkflowConfig

    workflow = WorkflowConfig(
        name="test",
        stages=[StageConfig(name="plan", agent="Arch", gate=GateConfig(type="approval"))],
    )
    registry = AgentRegistry.from_configs([
        {
            "name": "Arch",
            "description": "Plans",
            "capabilities": ["code_analysis"],
            "tools": ["code"],
            "default_model": "anthropic/claude-opus-4-6",
            "system_prompt": "You are an architect.",
        }
    ])

    orch = FleetOrchestrator(task_id="t-1", workflow=workflow, registry=registry)
    mock_checkpointer = MagicMock()

    with patch("agent_fleet.core.orchestrator.StateGraph") as mock_sg_cls:
        mock_graph = MagicMock()
        mock_sg_cls.return_value = mock_graph
        orch.build_graph(checkpointer=mock_checkpointer)

    mock_graph.compile.assert_called_once_with(checkpointer=mock_checkpointer)


def test_build_graph_works_without_checkpointer():
    """build_graph() with no checkpointer still works (backward compat)."""
    from unittest.mock import MagicMock, patch

    from agent_fleet.agents.registry import AgentRegistry
    from agent_fleet.core.orchestrator import FleetOrchestrator
    from agent_fleet.core.workflow import GateConfig, StageConfig, WorkflowConfig

    workflow = WorkflowConfig(
        name="test",
        stages=[StageConfig(name="plan", agent="Arch", gate=GateConfig(type="approval"))],
    )
    registry = AgentRegistry.from_configs([
        {
            "name": "Arch",
            "description": "Plans",
            "capabilities": ["code_analysis"],
            "tools": ["code"],
            "default_model": "anthropic/claude-opus-4-6",
            "system_prompt": "You are an architect.",
        }
    ])

    orch = FleetOrchestrator(task_id="t-1", workflow=workflow, registry=registry)

    with patch("agent_fleet.core.orchestrator.StateGraph") as mock_sg_cls:
        mock_graph = MagicMock()
        mock_sg_cls.return_value = mock_graph
        orch.build_graph()

    mock_graph.compile.assert_called_once_with(checkpointer=None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_orchestrator.py::test_build_graph_passes_checkpointer -v`
Expected: FAIL — `TypeError: build_graph() got an unexpected keyword argument 'checkpointer'`

- [ ] **Step 3: Update build_graph signature**

In `src/agent_fleet/core/orchestrator.py`, change line 532:

From:
```python
    def build_graph(self) -> StateGraph:
```
To:
```python
    def build_graph(self, checkpointer: "BaseCheckpointSaver | None" = None):
```

Add import at top of file:
```python
from __future__ import annotations
```

And change line 560:

From:
```python
        return graph.compile()
```
To:
```python
        return graph.compile(checkpointer=checkpointer)
```

- [ ] **Step 4: Run ALL orchestrator tests**

Run: `pytest tests/unit/test_orchestrator.py tests/unit/test_orchestrator_wired.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_fleet/core/orchestrator.py tests/unit/test_orchestrator.py
git commit -m "feat(orchestrator): build_graph() accepts optional checkpointer (#184)"
```

---

## Task 3.5: Update `atomic_pickup` + Fix Existing Worker Tests

**Files:**
- Modify: `src/agent_fleet/store/supabase_repo.py` (atomic_pickup method)
- Modify: `tests/unit/test_worker.py` (fixture + assertions)

- [ ] **Step 1: Update `atomic_pickup` to accept both statuses**

In `src/agent_fleet/store/supabase_repo.py`, find the `atomic_pickup` method. Change:

```python
        .eq("status", "queued")
```
To:
```python
        .in_("status", ["queued", "resuming"])
```

- [ ] **Step 2: Update `tests/unit/test_worker.py` fixture to mock checkpointer**

In the `worker` fixture, add `get_checkpointer` to the patches:

```python
@pytest.fixture
def worker(mock_service_client):
    with patch("agent_fleet.worker.get_service_client", return_value=mock_service_client), \
         patch("agent_fleet.worker.get_checkpointer") as mock_cp:
        mock_cp.return_value = MagicMock()
        w = FleetWorker(max_concurrent_tasks=2, poll_interval_seconds=0.1)
        yield w
        w.shutdown()
```

- [ ] **Step 3: Update stale recovery test assertions**

Change `test_recovers_stale_running_tasks_on_startup` assertion from:
```python
worker._tasks_repo.update_status.assert_called_with("task-old", "queued")
```
To:
```python
worker._tasks_repo.update_status.assert_called_with("task-old", "resuming")
```

Do the same for `test_recover_stale_tasks_no_started_at`:
```python
worker._tasks_repo.update_status.assert_called_with("task-notime", "resuming")
```

- [ ] **Step 4: Update fetch mock chain in poll tests**

In `test_picks_up_queued_task`, the mock chain uses `.eq.return_value.order...` — update to `.in_.return_value.order...`:

```python
chain = mock_service_client.table.return_value.select.return_value
chain.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [task_row]
```

- [ ] **Step 5: Run existing worker tests**

Run: `pytest tests/unit/test_worker.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/agent_fleet/store/supabase_repo.py tests/unit/test_worker.py
git commit -m "fix(store): atomic_pickup accepts both queued and resuming statuses (#184)"
```

---

## Task 4: Add Resume Logic to Worker

**Files:**
- Modify: `src/agent_fleet/worker/__init__.py`
- Create: `tests/unit/test_worker_resume.py`

- [ ] **Step 1: Write failing tests for resume logic**

```python
# tests/unit/test_worker_resume.py
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
    def _make_task(self, status: str = "queued") -> dict:
        return {
            "id": "task-resume",
            "repo": "/tmp/repo",
            "description": "Do something",
            "workflow_id": "wf-1",
            "user_id": "user-1",
            "status": status,
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

        # Should invoke with initial_state dict (not None)
        call_args = mock_graph.invoke.call_args
        assert call_args[0][0] is not None  # first positional arg is initial_state
        assert call_args[0][0]["task_id"] == "task-resume"

    def test_resuming_task_checks_checkpoint(self, worker):
        """Resuming task calls graph.get_state() to check for checkpoint."""
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

        # Should check for checkpoint
        mock_graph.get_state.assert_called_once()
        # Should invoke with None (resume from checkpoint)
        call_args = mock_graph.invoke.call_args
        assert call_args[0][0] is None

    def test_resuming_task_no_checkpoint_falls_back_to_fresh(self, worker):
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

        # Should invoke with initial_state (fresh start)
        call_args = mock_graph.invoke.call_args
        assert call_args[0][0] is not None
        assert call_args[0][0]["task_id"] == "task-resume"


class TestCheckpointCleanup:
    def test_checkpoint_cleaned_after_completion(self, worker):
        """Checkpoint is deleted after task completes."""
        task = {"id": "task-done", "repo": "/tmp/repo", "description": "x",
                "workflow_id": "wf-1", "user_id": "u-1", "status": "queued"}
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

        # Checkpointer.delete should have been called
        worker._checkpointer.delete.assert_called_once()

    def test_checkpoint_cleanup_failure_is_non_fatal(self, worker):
        """If checkpoint cleanup fails, task still completes normally."""
        task = {"id": "task-done", "repo": "/tmp/repo", "description": "x",
                "workflow_id": "wf-1", "user_id": "u-1", "status": "queued"}
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

        worker._checkpointer.delete.side_effect = RuntimeError("DB gone")

        with patch("agent_fleet.worker.OrchestratorFactory") as mock_factory, \
             patch("agent_fleet.worker.WorktreeManager"):
            mock_factory.from_supabase.return_value = mock_writer
            # Should not raise
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


class TestFetchBothStatuses:
    def test_fetch_picks_up_queued_and_resuming(self, worker, mock_service_client):
        """_fetch_queued_tasks returns both queued and resuming tasks."""
        mock_service_client.table.return_value.select.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": "t-1", "status": "queued"},
            {"id": "t-2", "status": "resuming"},
        ]

        tasks = worker._fetch_queued_tasks(limit=5)
        assert len(tasks) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_worker_resume.py -v`
Expected: FAIL — multiple failures (worker doesn't have checkpointer, no resume logic, etc.)

- [ ] **Step 3: Update FleetWorker.__init__ to create checkpointer**

In `src/agent_fleet/worker/__init__.py`, add import at top:

```python
from agent_fleet.worker.checkpointer import get_checkpointer
```

In `__init__` method (after line 45), add:

```python
        self._checkpointer = get_checkpointer()
```

- [ ] **Step 4: Update `_fetch_queued_tasks` to pick up both statuses**

Replace the current method (lines 126-136):

```python
    def _fetch_queued_tasks(self, limit: int = 5) -> list[dict]:
        """Fetch queued and resuming tasks from Supabase, ordered by created_at."""
        result = (
            self._client.table("tasks")
            .select("*")
            .in_("status", ["queued", "resuming"])
            .order("created_at")
            .limit(limit)
            .execute()
        )
        return result.data
```

- [ ] **Step 5: Update `_recover_stale_tasks` to set `resuming` status**

In `_recover_stale_tasks` (lines 221-243), change all occurrences of:
```python
self._tasks_repo.update_status(task["id"], "queued")
```
To:
```python
self._tasks_repo.update_status(task["id"], "resuming")
```

There are two occurrences: line 230 (no started_at) and line 243 (stale).

- [ ] **Step 6: Update `_execute_task` with resume logic and checkpoint cleanup**

Replace the `_execute_task` method (lines 138-211) with:

```python
    def _execute_task(self, task: dict) -> None:
        """Execute a single task through the orchestrator pipeline."""
        task_id = task["id"]
        is_resuming = task.get("status") == "resuming"
        logger.info("task_executing", task_id=task_id, resuming=is_resuming)

        config = {"configurable": {"thread_id": task_id}}

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

            graph = orchestrator.build_graph(checkpointer=self._checkpointer)

            if is_resuming:
                try:
                    existing_state = graph.get_state(config)
                except Exception as cp_read_err:
                    logger.warning("checkpoint_read_failed", task_id=task_id, error=str(cp_read_err))
                    existing_state = None
                if existing_state and existing_state.values:
                    logger.info(
                        "task_resuming_from_checkpoint",
                        task_id=task_id,
                        stage=existing_state.values.get("current_stage"),
                    )
                    result = graph.invoke(None, config)
                else:
                    logger.warning("no_checkpoint_found", task_id=task_id)
                    initial_state = self._build_initial_state(task, workflow_data)
                    result = graph.invoke(initial_state, config)
            else:
                initial_state = self._build_initial_state(task, workflow_data)
                result = graph.invoke(initial_state, config)

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

            # Only clean up checkpoint on successful terminal completion.
            # On error, preserve checkpoint so task can be resumed.
            if final_status in ("completed", "error"):
                try:
                    self._cleanup_checkpoint(task_id, config)
                except Exception as cp_err:
                    logger.warning("checkpoint_cleanup_failed", task_id=task_id, error=str(cp_err))

        except Exception as e:
            logger.error("task_failed", task_id=task_id, error=str(e))
            try:
                self._tasks_repo.update_status(
                    task_id, "error", error_message=str(e)[:1000]
                )
                self._events_repo.append(task_id, "task_error", {"error": str(e)})
            except Exception as write_err:
                logger.error("status_write_failed", task_id=task_id, error=str(write_err))
            # NOTE: Do NOT clean checkpoint on crash — preserve for resume

        finally:
            # Worktree cleanup
            try:
                from pathlib import Path

                from agent_fleet.workspace.worktree import WorktreeManager

                repo_path = task.get("repo")
                if repo_path:
                    wt_manager = WorktreeManager(Path(repo_path))
                    wt_manager.cleanup_all(task_id)
                    logger.info("worktrees_cleaned", task_id=task_id)
            except Exception as cleanup_err:
                logger.error(
                    "worktree_cleanup_failed", task_id=task_id, error=str(cleanup_err)
                )

    def _cleanup_checkpoint(self, task_id: str, config: dict) -> None:
        """Delete checkpoint data for a completed task."""
        self._checkpointer.delete(config)
        logger.info("checkpoint_cleaned", task_id=task_id)

    def _build_initial_state(self, task: dict, workflow_data: dict) -> dict:
        """Build initial FleetState for a fresh task."""
        return {
            "task_id": task["id"],
            "repo": task["repo"],
            "description": task["description"],
            "workflow_name": workflow_data.get("name", "unknown"),
            "status": "running",
            "completed_stages": [],
            "stage_outputs": {},
            "total_tokens": 0,
            "total_cost_usd": 0.0,
        }
```

- [ ] **Step 7: Run resume tests to verify they pass**

Run: `pytest tests/unit/test_worker_resume.py -v`
Expected: All 7 tests PASS

- [ ] **Step 8: Run ALL worker tests to verify backward compat**

Run: `pytest tests/unit/test_worker.py tests/unit/test_worker_resume.py -v`
Expected: All tests PASS

**NOTE:** The existing `test_worker.py` tests may need their fixtures updated to mock `get_checkpointer` — they were written before checkpoint support. If they fail with `RuntimeError: SUPABASE_DB_URL not configured`, add `patch("agent_fleet.worker.get_checkpointer")` to the `worker` fixture.

- [ ] **Step 9: Commit**

```bash
git add src/agent_fleet/worker/__init__.py tests/unit/test_worker_resume.py
git commit -m "feat(worker): add checkpoint resume logic and cleanup (#184)"
```

---

## Task 5: Update Docker Compose and Environment

**Files:**
- Modify: `docker-compose.yml:34-40`

- [ ] **Step 1: Add SUPABASE_DB_URL to worker environment**

In `docker-compose.yml`, add to the worker service's environment section (after line 36):

```yaml
      SUPABASE_DB_URL: ${SUPABASE_DB_URL}
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(docker): add SUPABASE_DB_URL for checkpoint persistence (#184)"
```

---

## Task 6: Update CLAUDE.md and Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/user-guide.md` (ops appendix)

- [ ] **Step 1: Update CLAUDE.md principle #7**

Find:
```
7. **Fail-safe by default** — Every agent execution has a `timeout_minutes` kill
   switch and a `max_tokens` budget. Worktrees are cleaned up in `finally` blocks.
   Crashed tasks auto-resume from LangGraph checkpoints on API restart.
```

Replace with:
```
7. **Fail-safe by default** — Every agent execution has a `timeout_minutes` kill
   switch and a `max_tokens` budget. Worktrees are cleaned up in `finally` blocks.
   Crashed tasks auto-resume from LangGraph Postgres checkpoints on worker restart.
   Checkpoints are stored in Supabase Postgres via `langgraph-checkpoint-postgres`
   and cleaned up after task completion.
```

- [ ] **Step 2: Add SUPABASE_DB_URL to Known Pitfalls**

Add to the Known Pitfalls section:
```
- **SUPABASE_DB_URL** — This is the direct Postgres connection string, not
  the Supabase REST API URL. Required for checkpoint crash recovery. Find it
  in Supabase dashboard under Project Settings > Database > Connection string.
```

- [ ] **Step 3: Update user-guide.md ops appendix env vars table**

Add a row for `SUPABASE_DB_URL` to the environment variables table in the Operations Guide appendix.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/user-guide.md
git commit -m "docs: update docs for checkpoint crash recovery (#184)"
```

---

## Task 7: Final Integration — Verify Full Test Suite

**Files:**
- All modified and new files

- [ ] **Step 1: Run lint**

Run: `ruff check src/ cli/ tests/`
Expected: No errors

- [ ] **Step 2: Run format**

Run: `ruff format src/ cli/ tests/`

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/unit/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 4: Fix any remaining issues**

- [ ] **Step 5: Commit fixes if any**

```bash
git add -A
git commit -m "fix: lint and test fixes for checkpoint crash recovery (#184)"
```

---

## Execution Order

```
Task 1 (deps) → Task 2 (checkpointer factory) → Task 3 (build_graph param)
                                                        ↓
                                                  Task 3.5 (atomic_pickup + test fixes)
                                                        ↓
                                                  Task 4 (resume logic)
                                                        ↓
                                              Task 5 (docker) + Task 6 (docs)
                                                        ↓
                                                  Task 7 (final verify)
```

Tasks 1-3 are sequential (each depends on the previous).
Task 3.5 can run after Task 1 (needs checkpointer import mock).
Task 4 depends on Tasks 2, 3, and 3.5.
Tasks 5 and 6 can run in parallel after Task 4.
Task 7 runs last.
