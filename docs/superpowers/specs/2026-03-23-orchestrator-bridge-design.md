# Orchestrator-to-UI Bridge — Design Spec

**EPIC:** #177 — Bridge Orchestrator to UI — End-to-End Task Execution
**Date:** 2026-03-23
**Status:** Approved

---

## Problem

The orchestrator (`FleetOrchestrator` + `TaskWorker` + LangGraph) is fully implemented but only runs via CLI. The UI writes tasks to Supabase, the backend uses SQLAlchemy/SQLite — two disconnected data layers. When a user submits a task from the UI, nothing picks it up. Dashboard and TaskMonitor always show stale data because no process writes status updates back to Supabase.

## Decision Record

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Worker topology | Separate process (`fleet-worker`) | Resilient to API restarts, scales independently, isolates heavy compute from HTTP serving |
| Data layer | Drop SQLAlchemy, use `supabase-py` everywhere | Supabase repos already exist, richer schema, single migration system, Realtime works out of the box |
| Task pickup | Poll-based (3s interval) | Simplest, most robust, no extra infra. 3s latency is invisible for multi-minute tasks |
| Status writing | Composition wrapper (`StatusWriter`) | Keeps orchestrator.py pure, worker owns the persistence layer |
| Worker threading model | Synchronous (ThreadPoolExecutor, not asyncio) | Orchestrator uses blocking `subprocess.run` calls; async would freeze the event loop. Converting to async is a future optimization |

---

## Architecture

```
┌────────────┐      ┌──────────────┐      ┌─────────────────┐
│  React UI  │─────▶│   Supabase   │◀─────│  fleet-worker   │
│ (port 3001)│◀─────│  (Postgres)  │─────▶│  (new process)  │
└────────────┘  RT  └──────────────┘ poll  └────────┬────────┘
                           ▲                        │
                           │                        ▼
                    ┌──────┴──────┐       ┌─────────────────┐
                    │  FastAPI    │       │ FleetOrchestrator│
                    │  (port 8000)│       │ + LangGraph      │
                    └─────────────┘       └─────────────────┘
```

**Three processes, one database:**
- `uvicorn` — API server (auth, CRUD, WebSocket chat)
- `fleet-worker` — task execution (orchestrator, agents, LLM calls)
- Supabase — single source of truth

**Data flow:**
1. User submits task via UI → API validates → row inserted into Supabase `tasks` (`status='queued'`)
2. `fleet-worker` polls every 3s → finds queued task → sets `status='running'`
3. Worker loads workflow + agent configs from Supabase → builds LangGraph → runs orchestrator
4. `StatusWriter` writes `executions`, `gate_results`, `events` to Supabase as stages progress
5. UI receives live updates via Supabase Realtime (already wired in Dashboard + TaskMonitor)
6. On completion → `status='completed'`, `pr_url` set

---

## Component Design

### 1. Drop SQLAlchemy, Rewire API to Supabase

**Remove:**
- `SQLAlchemy`, `Alembic` dependencies from `pyproject.toml`
- `create_engine`, `sessionmaker`, `Base`, `StaticPool` from `main.py`
- `src/agent_fleet/store/models.py` (ORM models: TaskRecord, ExecutionRecord, etc.)
- `src/agent_fleet/store/repository.py` (SQLAlchemy repository)
- `agent_fleet.db` file

**Keep:**
- `src/agent_fleet/store/supabase_repo.py` — becomes the only data layer
- All Supabase migrations in `supabase/migrations/`

**New shared dependency (`src/agent_fleet/api/deps.py`):**

```python
def get_supabase_client() -> Client:
    """Anon client for API routes — RLS enforced via JWT."""

def get_service_client() -> Client:
    """Service role client for worker — bypasses RLS."""

def get_current_user(request: Request) -> dict:
    """Validate JWT from Authorization header, return user_id."""
```

- API routes: `client = Depends(get_supabase_client)` + `user = Depends(get_current_user)`
- Worker: uses `get_service_client()` directly (no HTTP context)

### 2. Worker Process (`fleet-worker`)

**Entry point:** `src/agent_fleet/worker/__init__.py` → `python -m agent_fleet.worker`

**Poll loop:**
```
while running:
    1. Query tasks WHERE status='queued' ORDER BY created_at LIMIT 5
    2. For each task — atomic pickup (compare-and-swap):
       - UPDATE tasks SET status='running', started_at=now()
         WHERE id=X AND status='queued'
       - Check rowcount == 1; skip if 0 (another worker grabbed it)
       - Load workflow from Supabase by workflow_id
       - Convert workflow stages (JSONB) → WorkflowConfig (Pydantic)
       - Load agent configs from Supabase for each stage's agent
       - Build orchestrator via OrchestratorFactory.from_supabase(workflow, agents)
       - Submit to ThreadPoolExecutor
    3. Sleep 3 seconds
```

**Atomic task pickup:** The compare-and-swap (`WHERE id=X AND status='queued'`) prevents double-pickup even if multiple workers run concurrently or a single worker restarts rapidly. No advisory locks needed for single-worker deployments.

**Concurrency control:**
- `max_concurrent_tasks` setting (default: 3) — skip pickup if at capacity
- Respect `workflow.concurrency` per repo — no 2 tasks on same repo simultaneously
- `ThreadPoolExecutor(max_workers=5)` — inherited from current TaskWorker pattern

**Graceful shutdown:**
- SIGINT/SIGTERM handler sets `running = False`
- Wait for in-flight tasks to complete (with configurable timeout, default 5 min)
- Any still-running tasks set back to `status='queued'` for re-pickup on restart

**Docker service:**
```yaml
worker:
  build: .
  command: python -m agent_fleet.worker
  environment:
    SUPABASE_URL: ${SUPABASE_URL}
    SUPABASE_SERVICE_ROLE_KEY: ${SUPABASE_SERVICE_ROLE_KEY}
    ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
    OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    MAX_CONCURRENT_TASKS: ${MAX_CONCURRENT_TASKS:-3}
    POLL_INTERVAL_SECONDS: ${POLL_INTERVAL_SECONDS:-3}
  volumes:
    - ./config:/app/config
    - worker-worktrees:/tmp/fleet-worktrees
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

### 3. Orchestrator Adaptation Layer

The current `FleetOrchestrator.__init__` accepts `workflow_path: Path` and `agents_dir: Path` — it reads YAML from disk. The worker loads config from Supabase as JSONB. We need a factory that bridges this gap.

**New: `src/agent_fleet/worker/orchestrator_factory.py`**

```python
class OrchestratorFactory:
    @staticmethod
    def from_supabase(
        workflow_data: dict,        # Supabase workflows row
        agent_configs: list[dict],  # Supabase agents rows
        task_id: str,
        repos: dict,                # Supabase repository instances
    ) -> "StatusWriter":
        """Build a StatusWriter (persistence-aware orchestrator) from Supabase data."""
        # 1. Convert workflow JSONB → WorkflowConfig (Pydantic)
        workflow = WorkflowConfig(**workflow_data)

        # 2. Convert agent rows → dict[str, AgentConfig]
        registry = AgentRegistry.from_configs(agent_configs)

        # 3. Construct StatusWriter (subclass of FleetOrchestrator)
        return StatusWriter(
            repos=repos,
            workflow=workflow,
            registry=registry,
            task_id=task_id,
        )
```

The factory returns a `StatusWriter` (not a plain `FleetOrchestrator`), so the worker gets persistence for free:
```python
# In the worker poll loop:
orchestrator = OrchestratorFactory.from_supabase(workflow_data, agent_configs, task_id, repos)
graph = orchestrator.build_graph()
result = graph.invoke(initial_state)
```

**Orchestrator constructor changes (minimal):**

New `FleetOrchestrator.__init__` signature:
```python
def __init__(
    self,
    task_id: str,
    # New: accept in-memory config directly
    workflow: WorkflowConfig | None = None,
    registry: AgentRegistry | None = None,
    # Legacy: accept file paths (CLI backward compat)
    workflow_path: Path | None = None,
    agents_dir: Path | None = None,
    repo_path: Path | None = None,
):
    if workflow and registry:
        self.workflow = workflow
        self.registry = registry
    elif workflow_path and agents_dir:
        self.workflow = load_workflow(workflow_path)
        self.registry = AgentRegistry(agents_dir)
    else:
        raise ValueError("Provide either (workflow, registry) or (workflow_path, agents_dir)")
```

- `AgentRegistry` gets a new `from_configs(configs: list[dict])` classmethod that builds from dicts instead of scanning a YAML directory

This is the smallest change that bridges both entry points (CLI + worker) without rewriting the orchestrator internals.

### 4. StatusWriter — Orchestrator Persistence Layer

Wraps the orchestrator's state graph nodes with Supabase writes. Keeps `orchestrator.py` core logic unchanged.

**Location:** `src/agent_fleet/worker/status_writer.py`

**Write points:**

| Orchestrator Event | Supabase Write |
|---|---|
| `route_next` selects stage(s) | `tasks.update(current_stage=stage_name)` |
| `execute_stage` starts | `executions.create(stage, agent, model, status='running')` |
| `execute_stage` completes | `executions.update(status='completed', summary, tokens, files_changed)` |
| `execute_stage` fails | `executions.update(status='error', summary=error_msg)` |
| `evaluate_gate` result | `gate_results.create(execution_id, gate_type, passed, score, details)` |
| Gate triggers retry | `executions.create(...)` — new execution row for the retry |
| `execute_stage` completes (cost) | Compute cost from `LLMResponse.tokens_used` + model via `litellm.cost_per_token()`, accumulate in state |
| Pipeline completes | `tasks.update(status='completed', completed_stages, total_tokens, total_cost_usd, pr_url)` |
| Pipeline errors | `tasks.update(status='error', error_message=...)` |
| Any event | `events.append(task_id, event_type, payload)` |

**Relationship to existing `log_event`:** The orchestrator already calls `log_event()` internally (defined in `core/events.py`). Rather than duplicating events, the StatusWriter replaces `log_event` by injecting a callback that writes to Supabase. The existing `log_event` calls inside the orchestrator are redirected — not supplemented — so there are no duplicate events.

**Cancellation check:** Before each node execution, the StatusWriter queries `tasks.get(task_id)` and checks if `status='cancelled'`. If cancelled, it sets the state to `interrupted` which triggers the LangGraph conditional edge to `__end__`. In-flight LLM calls are not interrupted mid-stream — cancellation takes effect at the next stage boundary.

**Composition mechanism:** The StatusWriter subclasses `FleetOrchestrator` and overrides `route_next`, `execute_stage`, and `evaluate_gate` to add Supabase writes before/after calling `super()`. The worker then calls `build_graph()` on the `StatusWriter` instance, producing a LangGraph that inherently includes persistence.

```python
class StatusWriter(FleetOrchestrator):
    def __init__(self, repos, **kwargs):
        super().__init__(**kwargs)
        self.repos = repos

    def route_next(self, state):
        # Check cancellation
        task = self.repos.tasks.get(state['task_id'])
        if task['status'] == 'cancelled':
            return {**state, 'status': 'interrupted'}
        result = super().route_next(state)
        self.repos.tasks.update_status(state['task_id'], current_stage=result.get('current_stage'))
        return result

    def execute_stage(self, state):
        # Create execution record, call super, update on completion/failure
        ...

    def evaluate_gate(self, state):
        # Call super, write gate_result
        ...
```

### 5. API Route Updates

**Tasks routes (`src/agent_fleet/api/routes/tasks.py`):**

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/api/v1/tasks` | Validate → insert to Supabase (`status='queued'`, stores `project_id` if provided) → return task |
| `GET` | `/api/v1/tasks` | List user's tasks (scoped by JWT `user_id`) |
| `GET` | `/api/v1/tasks/{id}` | Task + executions + gate_results (joined) |
| `DELETE` | `/api/v1/tasks/{id}/cancel` | Set `status='cancelled'`, worker checks before each stage |

**Updated Pydantic schemas:**

```python
class TaskSubmitRequest(BaseModel):
    repo: str
    description: str
    workflow_id: UUID
    project_id: UUID | None = None

class TaskResponse(BaseModel):
    id: UUID
    repo: str
    description: str
    status: str  # queued, running, completed, error, cancelled
    workflow_name: str
    current_stage: str | None
    completed_stages: list[str]
    total_tokens: int
    total_cost_usd: float
    pr_url: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
```

**All other route files** (`agents.py`, `workflows.py`, `profile.py`, etc.): same pattern — swap SQLAlchemy session for Supabase client + `get_current_user`.

### 6. UI Change

**`SubmitTask.tsx`:** Switch from direct Supabase insert to `POST /api/v1/tasks` via the API. API handles validation, returns proper errors.

No other UI changes needed — Dashboard and TaskMonitor already subscribe to Supabase Realtime on `tasks`, `executions`, and `events`. Once the worker writes data, the UI updates automatically.

---

## Scope Boundaries

**In scope (this EPIC):**
1. Remove SQLAlchemy — delete ORM models, repository, engine setup
2. New `src/agent_fleet/api/deps.py` — Supabase clients + JWT auth dependency
3. Rewire all API routes to Supabase repos
4. New `src/agent_fleet/worker/` — poll loop, task pickup, concurrency, shutdown
5. New `src/agent_fleet/worker/status_writer.py` — wraps orchestrator with Supabase writes
6. Update `docker-compose.yml` — add worker service
7. Update `SubmitTask.tsx` — call API instead of direct Supabase insert
8. Tests — unit tests for worker, status writer, updated routes

**Out of scope (tracked in other EPICs):**
- Chat → LLM wiring (EPIC #193)
- Project detail / edit / delete (EPIC #185)
- Workflow designer CRUD (EPIC #200)
- Project selector in Submit Task (EPIC #185, #189)
- LangGraph checkpoint crash recovery (#184)
- Multi-worker `FOR UPDATE SKIP LOCKED` (future, architecture supports it)

---

## File Inventory

**New files:**
- `src/agent_fleet/api/deps.py`
- `src/agent_fleet/api/schemas/tasks.py` (updated Pydantic models)
- `src/agent_fleet/worker/__init__.py`
- `src/agent_fleet/worker/__main__.py`
- `src/agent_fleet/worker/status_writer.py`
- `tests/unit/test_worker.py`
- `tests/unit/test_status_writer.py`
- `tests/unit/test_deps.py`
- `tests/unit/test_orchestrator_factory.py`

**Modified files:**
- `src/agent_fleet/main.py` — remove SQLAlchemy, use Supabase client
- `src/agent_fleet/api/routes/tasks.py` — rewrite to Supabase
- `src/agent_fleet/api/routes/agents.py` — rewrite to Supabase
- `src/agent_fleet/api/routes/workflows.py` — rewrite to Supabase
- `src/agent_fleet/api/routes/profile.py` — rewrite to Supabase
- `src/agent_fleet/api/routes/chat.py` — rewrite to Supabase
- `src/agent_fleet/api/routes/api_keys.py` — rewrite to Supabase
- `src/agent_fleet/api/routes/approvals.py` — rewrite to Supabase
- `src/agent_fleet/api/routes/audit.py` — rewrite to Supabase
- `src/agent_fleet/store/supabase_repo.py` — add missing methods if needed
- `docker-compose.yml` — add worker service
- `fleet-ui/src/pages/SubmitTask/SubmitTask.tsx` — call API
- `pyproject.toml` — remove sqlalchemy/alembic deps

**Deleted files:**
- `src/agent_fleet/store/models.py`
- `src/agent_fleet/store/repository.py`
- `agent_fleet.db` (if exists)
- `alembic/` directory (if exists)

---

## Supabase Repository Additions

The existing `supabase_repo.py` needs these additions:

**New class: `SupabaseGateResultRepository`**
- `create(execution_id, gate_type, passed, score, details)` → insert gate result
- `list_by_execution(execution_id)` → ordered by created_at

**Updated: `SupabaseExecutionRepository`**
- `update_status` needs additional fields: `tokens_used`, `files_changed` (JSONB), `finished_at`

**Updated: `SupabaseTaskRepository`**
- `list_by_status` needs `limit` and `order_by` parameters for worker pickup query
- `atomic_pickup(task_id)` → `.update({"status": "running", ...}).eq("id", X).eq("status", "queued").execute()` — check `len(result.data) == 1` to confirm pickup succeeded (supabase-py does not expose raw rowcount)

**Remove: `src/agent_fleet/store/supabase_client.py`**
- The existing module-level `_client` singleton violates the "no global state" rule
- Replace with factory functions in `deps.py` (API) and constructor injection (worker)

---

## Worktree Cleanup Strategy

The orchestrator creates worktrees per stage. Cleanup responsibility:

- **On stage success:** Orchestrator's existing `finally` block in `_execute_single_stage` cleans up
- **On task completion/error:** Worker calls `WorktreeManager.cleanup_all(task_id)` after the graph finishes (in a `finally` block)
- **On worker shutdown:** Worker iterates in-flight tasks and cleans up worktrees before re-queuing
- **Stale worktree GC:** A startup check scans `worker-worktrees` volume for directories older than 24h and removes them (handles cases where cleanup was missed due to crash)

**Stale task recovery on startup:** On boot, the worker queries for tasks with `status='running'` and `started_at` older than the workflow's `timeout_minutes` (default 30min). These are re-queued to `status='queued'` so they get picked up again. This handles SIGKILL, OOM, and ungraceful crashes where the shutdown handler never ran.

---

## Worker Health Check

The worker exposes health via a simple mechanism:

- Write `last_heartbeat` timestamp to a Supabase `worker_heartbeat` row (or simple file) every poll cycle
- Docker `healthcheck` reads this and fails if stale > 30s:
  ```yaml
  healthcheck:
    test: ["CMD", "python", "-m", "agent_fleet.worker", "--health"]
    interval: 15s
    timeout: 5s
    retries: 3
  ```
- The `--health` flag checks the heartbeat file/row and exits 0 (healthy) or 1 (stale)

---

## Breaking Changes

- `TaskSubmitRequest.workflow` (string name) → `TaskSubmitRequest.workflow_id` (UUID). This is acceptable because there are no external API consumers — the UI is the only client and will be updated simultaneously.
- SQLAlchemy removal means existing `agent_fleet.db` data is abandoned. Since this is dev/demo data with no production users, no migration is needed.

---

## Test Strategy

**Unit tests (mocked Supabase):**
- `test_worker.py`: Poll loop picks up queued tasks, respects concurrency limits, handles graceful shutdown, atomic pickup prevents double-execution, cancelled tasks are skipped
- `test_status_writer.py`: Each orchestrator event triggers the correct Supabase write, cancellation check works, errors are captured and written
- `test_deps.py`: JWT validation extracts user_id, invalid tokens return 401, anon vs service client creation
- `test_orchestrator_factory.py`: Supabase JSONB converts to WorkflowConfig correctly, agent configs build registry

**Integration tests (real Supabase, local):**
- Submit task via API → verify row in Supabase with status='queued'
- Worker picks up task → status transitions queued→running→completed
- StatusWriter creates execution and gate_result rows
- Cancellation: submit then cancel → worker stops at next stage boundary

**E2E test (Playwright):**
- Submit task from UI → Dashboard shows running → TaskMonitor shows stage progress

---

## Environment Variables

| Variable | Used By | Purpose |
|----------|---------|---------|
| `SUPABASE_URL` | API + Worker | Supabase project URL |
| `SUPABASE_ANON_KEY` | API | Client-side, RLS enforced |
| `SUPABASE_SERVICE_ROLE_KEY` | Worker | Bypasses RLS for cross-user task pickup |
| `ANTHROPIC_API_KEY` | Worker | LLM calls via LiteLLM |
| `OPENAI_API_KEY` | Worker | LLM calls via LiteLLM |
| `MAX_CONCURRENT_TASKS` | Worker | Default: 3 |
| `POLL_INTERVAL_SECONDS` | Worker | Default: 3 |
