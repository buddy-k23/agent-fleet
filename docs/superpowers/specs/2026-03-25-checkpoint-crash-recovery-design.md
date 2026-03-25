# LangGraph Checkpoint Crash Recovery — Design Spec

**EPIC:** #184 — LangGraph Checkpoint Crash Recovery
**Date:** 2026-03-25
**Status:** Approved

---

## Problem

When the worker process crashes mid-task (OOM, SIGKILL, host failure), all in-memory LangGraph state is lost. The current recovery mechanism (`_recover_stale_tasks`) re-queues the task with `status='queued'`, causing the entire workflow to restart from stage 1 — losing all prior progress. For multi-stage pipelines that take 10-30 minutes, this wastes significant time and LLM cost.

## Decision Record

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Checkpoint backend | Postgres via Supabase | Single database, survives container restarts, supports multi-worker |
| Checkpoint library | `langgraph-checkpoint-postgres` | Official LangGraph package, auto-creates tables, handles serialization |
| Resume trigger | New `resuming` status | Distinguishes fresh starts from crash recovery in `_execute_task` |
| Checkpoint lifecycle | Delete after task completes/errors | Prevents unbounded table growth |
| Thread ID | `task_id` | Natural 1:1 mapping between tasks and checkpoint threads |

---

## Architecture

```
Worker restarts
    │
    ▼
_recover_stale_tasks()
    │
    ├── task.status = 'running' AND started_at > 30 min ago
    │       │
    │       ▼
    │   UPDATE status = 'resuming'  (not 'queued')
    │
    ▼
_poll_once()
    │
    ├── Picks up status IN ('queued', 'resuming')
    │
    ▼
_execute_task(task)
    │
    ├── task was 'resuming'?
    │       │
    │       ├── YES → graph.get_state(config)
    │       │       │
    │       │       ├── Checkpoint exists → graph.invoke(None, config)  # resume
    │       │       └── No checkpoint → graph.invoke(initial_state, config)  # fresh
    │       │
    │       └── NO → graph.invoke(initial_state, config)  # fresh start
    │
    ▼
Task completes/errors
    │
    ▼
Delete checkpoint for thread_id
```

---

## Component Design

### 1. Checkpointer Factory — `src/agent_fleet/worker/checkpointer.py`

```python
from langgraph.checkpoint.postgres import PostgresSaver

def get_checkpointer() -> PostgresSaver:
    """Create a Postgres checkpointer using Supabase connection string.

    Uses SUPABASE_DB_URL env var (direct Postgres connection, not the REST API).
    Falls back to constructing from SUPABASE_URL if DB URL not set.
    """
```

- Called once at `FleetWorker.__init__`, stored as `self._checkpointer`
- Calls `checkpointer.setup()` on first use to auto-create checkpoint tables
- Connection string from `SUPABASE_DB_URL` env var (Supabase exposes direct Postgres access)

### 2. Orchestrator Change — `build_graph()`

Current signature:
```python
def build_graph(self) -> StateGraph:
    ...
    return graph.compile()
```

New signature:
```python
def build_graph(self, checkpointer=None):
    ...
    return graph.compile(checkpointer=checkpointer)
```

Minimal change — just pass through the checkpointer. CLI path continues to pass `None` (no checkpointing for local CLI runs).

### 3. Worker `_execute_task()` Change

```python
def _execute_task(self, task: dict) -> None:
    task_id = task["id"]
    is_resuming = task.get("status") == "resuming"

    config = {"configurable": {"thread_id": task_id}}

    # ... build orchestrator as before ...
    graph = orchestrator.build_graph(checkpointer=self._checkpointer)

    if is_resuming:
        # Check for existing checkpoint
        existing_state = graph.get_state(config)
        if existing_state and existing_state.values:
            # Resume from checkpoint
            logger.info("task_resuming", task_id=task_id,
                       stage=existing_state.values.get("current_stage"))
            result = graph.invoke(None, config)
        else:
            # No checkpoint found — fresh start
            logger.warning("no_checkpoint_found", task_id=task_id)
            result = graph.invoke(initial_state, config)
    else:
        # Fresh start (queued task)
        result = graph.invoke(initial_state, config)

    # ... final status update as before ...

    # Cleanup checkpoint after completion
    self._cleanup_checkpoint(task_id)
```

### 4. Stale Task Recovery Change

Current (`_recover_stale_tasks`):
```python
self._tasks_repo.update_status(task["id"], "queued")
```

New:
```python
self._tasks_repo.update_status(task["id"], "resuming")
```

And `_poll_once` / `_fetch_queued_tasks` updated to pick up both statuses:
```python
# Fetch tasks with status IN ('queued', 'resuming')
```

### 5. Checkpoint Cleanup

```python
def _cleanup_checkpoint(self, task_id: str) -> None:
    """Delete checkpoint data for completed/errored task."""
    try:
        config = {"configurable": {"thread_id": task_id}}
        # PostgresSaver supports deletion
        self._checkpointer.delete(config)
        logger.info("checkpoint_cleaned", task_id=task_id)
    except Exception as e:
        logger.warning("checkpoint_cleanup_failed", task_id=task_id, error=str(e))
```

Called in the `finally` block of `_execute_task`, after worktree cleanup.

### 6. StatusWriter Compatibility

No changes needed. The StatusWriter writes events and execution records as stages progress. On resume, it will:
- Skip creating duplicate execution records (the checkpoint resumes at the node boundary, so the StatusWriter's `execute_stage` fires only for new stages)
- Continue appending events from where it left off

One edge case: if the crash happened after `execute_stage` completed but before `evaluate_gate`, the gate evaluation will re-run. This is safe because gate evaluation is idempotent (it reads the stage output and scores it).

---

## Environment Variables

| Variable | Service | Required | Default | Description |
|----------|---------|----------|---------|-------------|
| `SUPABASE_DB_URL` | Worker | Yes (for checkpoints) | — | Direct Postgres connection string (e.g., `postgresql://postgres:password@db.xxx.supabase.co:5432/postgres`) |

This is the **direct database connection**, not the Supabase REST API URL. Supabase provides this under Project Settings → Database → Connection string.

---

## New Dependency

```toml
# pyproject.toml
"langgraph-checkpoint-postgres>=2.0.0",
"psycopg[binary]>=3.1.0",  # Required by langgraph-checkpoint-postgres
```

---

## Scope Boundaries

**In scope:**
1. `src/agent_fleet/worker/checkpointer.py` — factory function
2. `src/agent_fleet/core/orchestrator.py` — accept checkpointer param
3. `src/agent_fleet/worker/__init__.py` — resume logic, checkpoint cleanup, status changes
4. `pyproject.toml` — new deps
5. `docker-compose.yml` — add `SUPABASE_DB_URL` env var
6. Tests — unit tests for all changes

**Out of scope:**
- Checkpoint-based progress UI (showing which node was checkpointed) — future enhancement
- CLI checkpointing — CLI runs are short-lived, not worth the complexity
- Cross-worker checkpoint sharing — already works since Postgres is shared

---

## Test Strategy

**Unit tests (mocked checkpointer):**
- `test_checkpointer.py`: Factory creates PostgresSaver with correct connection string, setup() called
- `test_worker_resume.py`: Fresh task invokes with initial_state, resuming task checks checkpoint first, missing checkpoint falls back to fresh start
- `test_worker_cleanup.py`: Checkpoint deleted after task completes, deleted after task errors, cleanup failure logged but doesn't crash
- `test_recover_stale.py`: Stale tasks set to `resuming` not `queued`
- `test_orchestrator_checkpointer.py`: `build_graph(checkpointer=X)` passes X to `compile()`

---

## File Inventory

**New files:**
- `src/agent_fleet/worker/checkpointer.py`
- `tests/unit/test_checkpointer.py`

**Modified files:**
- `src/agent_fleet/core/orchestrator.py` — `build_graph()` accepts checkpointer
- `src/agent_fleet/worker/__init__.py` — resume logic, checkpoint cleanup, fetch both statuses
- `pyproject.toml` — new deps
- `docker-compose.yml` — `SUPABASE_DB_URL` env var
- `CLAUDE.md` — update principle #7 to reflect actual implementation
