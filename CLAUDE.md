# Agent Fleet — Claude Instructions

## Project Overview

Multi-model AI agent orchestration platform. Submits coding tasks, coordinates
specialized agents (Architect, Backend Dev, Frontend Dev, Reviewer, Tester),
evaluates quality gates, and produces PRs. Built on LangGraph + LiteLLM + FastAPI.

**Stack:** Python 3.12+, LangGraph, LiteLLM, FastAPI, Typer, Supabase (supabase-py)
**Directory:** `src/agent_fleet/` (core), `cli/` (CLI client), `fleet-ui/` (React UI)

---

## 7 Architecture Principles

1. **Orchestrator owns the flow** — All task routing, retries, and gate evaluation
   go through the LangGraph orchestrator. Agents never call other agents directly.
   Hub-and-spoke, no peer-to-peer.

2. **Agents are config, not code** — Adding a new agent means adding a YAML file
   to `config/agents/`. No Python code changes required. If you're writing a new
   .py file to add an agent, you're doing it wrong.

3. **LiteLLM for all model calls** — Never import openai, anthropic, or google SDKs
   directly. All LLM calls go through LiteLLM so any model (cloud or local) works
   with zero code changes.

4. **Tools are sandboxed** — Shell commands run in restricted scope. File operations
   are confined to the task's git worktree. Browser tools run in headless Playwright.
   Never give agents unrestricted system access.

5. **Worktree isolation** — Each agent task runs in its own git worktree. Agents
   never modify the main working tree. Merges happen only after gates pass.

6. **Event-sourced state** — Every agent action and environment observation is an
   append-only event stored in the Event table. Enables full replay and debugging.

7. **Fail-safe by default** — Every agent execution has a `timeout_minutes` kill
   switch and a `max_tokens` budget. Worktrees are cleaned up in `finally` blocks.
   Crashed tasks auto-resume from LangGraph checkpoints on API restart.

---

## Build & Test Commands

```bash
# Activate venv
source .venv/bin/activate

# Run API server
uvicorn agent_fleet.main:app --reload --port 8000

# Run worker (separate process — polls Supabase for queued tasks)
python -m agent_fleet.worker

# Run CLI
fleet --help
fleet run --repo /path/to/repo --task "Implement feature X"
fleet agents list
fleet status <task-id>

# Run tests
pytest tests/unit/
pytest tests/integration/
pytest --cov=agent_fleet --cov-report=term-missing

# Lint & format
ruff check src/ cli/ tests/
ruff format src/ cli/ tests/

# Type checking
mypy src/agent_fleet/

# Docker (API + Worker + UI)
docker compose up
```

---

## Implementation Rules

1. **Type hints everywhere** — All function signatures must have type hints.
   Use Pydantic models for data structures, not raw dicts.

2. **No hardcoded API keys** — All secrets come from environment variables
   or `.env` file. Never commit keys. `.env` is gitignored.

3. **Async by default** — FastAPI routes and LLM calls are async.
   Use `async/await`, not synchronous blocking calls.

4. **Tests first** — Write failing tests before implementation. Minimum
   80% coverage enforced by pytest-cov.

5. **No global state** — Use dependency injection via FastAPI's `Depends()`.
   No module-level mutable variables. Supabase clients use `@lru_cache`
   factories in `api/deps.py`, not module-level singletons.

6. **Pydantic for all API schemas** — Request/response models use Pydantic v2.
   Validate at the API boundary. Use `model_dump()` not `.dict()`.

7. **Structured logging** — Use `structlog` with JSON output. Every log
   entry includes `task_id` and `agent_name` when in an agent context.

8. **Error handling** — Custom exceptions in `exceptions.py`. FastAPI
   exception handlers in `api/`. Never swallow exceptions silently.

---

## Agent YAML Schema

Required fields for every agent definition:

```yaml
name: string           # Display name
description: string    # What this agent does (used by orchestrator for routing)
capabilities: [string] # What it can do (code_analysis, testing, review, etc.)
tools: [string]        # Tool categories: code, browser, search, shell, api
default_model: string  # LiteLLM model identifier
system_prompt: string  # Base system prompt for the agent
max_retries: int       # Max retry attempts on gate failure (default: 2)
timeout_minutes: int   # Max execution time (default: 30)
max_tokens: int        # Max LLM tokens per execution (default: 100000)
can_delegate: [string] # Agent names this agent can delegate subtasks to (default: [])
```

---

## Workflow YAML Schema

```yaml
name: string
concurrency: int             # Max parallel tasks per repo (default: 1)
max_cost_usd: float          # Kill switch — halt if cost exceeds this
classifier_mode: string      # suggest | override | disabled (default: suggest)
stages:
  - name: string
    agent: string            # References agent YAML name
    model: string            # Optional model override
    depends_on: string|list  # Stage(s) that must complete first
    gate:
      type: automated|score|approval|custom
      checks: [string]
      min_score: int
      on_fail: retry|route_to|halt
      route_target: string
      max_retries: int
    reactions:
      ci_failed:
        action: send_to_agent
        retries: 2
    actions: [string]
```

---

## Git & Commit Convention

```
feat(scope): short description
fix(scope): short description
test(scope): short description
refactor(scope): short description
docs(scope): short description
```

Scope is the module: `orchestrator`, `agents`, `api`, `cli`, `tools`, `workspace`, `store`, `worker`, `bridge`.
Always reference the issue number: `feat(agents): add registry (#7)`

---

## Key Directories

| Path | Purpose |
|------|---------|
| `src/agent_fleet/core/` | LangGraph orchestrator, state, gates, routing |
| `src/agent_fleet/agents/` | Agent runner, registry, base interface |
| `src/agent_fleet/tools/` | Tool implementations (code, browser, shell, etc.) |
| `src/agent_fleet/api/` | FastAPI routes, schemas, websocket, deps (auth + Supabase clients) |
| `src/agent_fleet/api/deps.py` | Supabase client factories + JWT auth dependency — all routes import from here |
| `src/agent_fleet/api/schemas/` | Pydantic v2 request/response models (tasks, etc.) |
| `src/agent_fleet/worker/` | Fleet worker process — polls Supabase, runs orchestrator, writes status |
| `src/agent_fleet/worker/status_writer.py` | StatusWriter — orchestrator subclass that persists to Supabase |
| `src/agent_fleet/worker/orchestrator_factory.py` | Builds StatusWriter from Supabase workflow + agent data |
| `src/agent_fleet/models/` | LiteLLM provider wrapper, model config |
| `src/agent_fleet/workspace/` | Git worktree management |
| `src/agent_fleet/store/` | Supabase repositories (tasks, executions, events, agents, workflows, gate_results) |
| `config/agents/` | Agent YAML definitions (also stored in Supabase for UI-created agents) |
| `config/workflows/` | Workflow YAML definitions (also stored in Supabase) |
| `cli/` | Typer CLI client |
| `fleet-ui/` | React UI (Vite + TypeScript + Supabase Realtime) |
| `tests/` | Unit and integration tests |

---

## Known Pitfalls

- **LiteLLM model strings** — Use the provider prefix: `anthropic/claude-opus-4-6`,
  `openai/gpt-4o`, `ollama/llama3`. Plain model names may route incorrectly.
- **Worktree cleanup** — Always clean up worktrees in a `finally` block.
  Leaked worktrees accumulate and fill disk.
- **LangGraph state** — State must be serializable (no functions, no open
  file handles). Use Pydantic models in the state schema.
- **Async + subprocess** — Use `asyncio.create_subprocess_exec`, not
  `subprocess.run` in async contexts. Blocking calls freeze the event loop.
- **Gate infinite loops** — Always enforce `max_retries` on gate failures.
  An agent that never passes review will loop forever without this guard.
- **Supabase timestamps** — Use `datetime.now(timezone.utc).isoformat()` for
  timestamps, NOT `"now()"`. supabase-py sends JSON, so `"now()"` is stored
  as a literal string, not a Postgres function call.
- **User scoping** — All API routes must filter by `user_id` from
  `get_current_user()` for defense-in-depth, even though RLS exists.
- **Worker vs API clients** — API uses anon key (`get_supabase_client`),
  worker uses service role key (`get_service_client`). Never use service
  role key in API routes.

---

## Architecture: Three Processes, One Database

```
┌────────────┐      ┌──────────────┐      ┌─────────────────┐
│  React UI  │─────▶│   Supabase   │◀─────│  fleet-worker   │
│ (port 3001)│◀─────│  (Postgres)  │─────▶│  (poll process) │
└────────────┘  RT  └──────────────┘ poll  └────────┬────────┘
                           ▲                        │
                           │                        ▼
                    ┌──────┴──────┐       ┌─────────────────┐
                    │  FastAPI    │       │ FleetOrchestrator│
                    │  (port 8000)│       │ + StatusWriter   │
                    └─────────────┘       └─────────────────┘
```

**Data flow:**
1. User submits task via UI → API validates → `tasks` row (`status='queued'`)
2. `fleet-worker` polls every 3s → atomic pickup → `status='running'`
3. Worker builds orchestrator via `OrchestratorFactory.from_supabase()`
4. `StatusWriter` writes executions, gate_results, events as stages progress
5. UI receives live updates via Supabase Realtime
6. On completion → `status='completed'`, `pr_url` set

---

## Supabase Integration

**Sole data layer** — auth, database, realtime, storage all via Supabase.
SQLAlchemy was removed in EPIC #177.

### Environment Variables

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=sb_publishable_...      # API routes (RLS enforced)
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...   # Worker (bypasses RLS)
ANTHROPIC_API_KEY=...                      # Worker — LLM calls via LiteLLM
OPENAI_API_KEY=...                         # Worker — LLM calls via LiteLLM
MAX_CONCURRENT_TASKS=3                     # Worker — max parallel tasks
POLL_INTERVAL_SECONDS=3                    # Worker — poll frequency
```

### Schema (7 tables, all with RLS)

| Table | Purpose | RLS |
|-------|---------|-----|
| `profiles` | User display name + preferences | `auth.uid() = id` |
| `agents` | Agent configs (replaces YAML) | `auth.uid() = user_id` |
| `workflows` | Workflow configs (replaces YAML) | `auth.uid() = user_id` |
| `tasks` | Pipeline executions | `auth.uid() = user_id` |
| `executions` | Per-stage agent runs | via tasks FK |
| `gate_results` | Quality gate outcomes | via executions FK |
| `events` | Append-only event log | via tasks FK |

### Auth Flow

1. UI: Supabase Auth (email/password) → JWT token
2. API: `get_current_user` dependency validates JWT, extracts `user_id`
3. All queries scoped to `user_id` (defense in depth with RLS)

### Key Rules

- **Never bypass RLS** — API routes use anon key (`get_supabase_client` from `deps.py`)
- **Service role key** — only for worker (`get_service_client`) and admin operations
- **Realtime** — enabled on tasks, executions, events tables
- **Storage** — `task-outputs` and `task-logs` buckets for agent artifacts
- **Seed data** — `python scripts/seed_supabase.py <user_id>` for default agents/workflows

---

## Worker Process (`fleet-worker`)

**Entry point:** `python -m agent_fleet.worker`

**Poll loop:** Every 3s, queries `tasks WHERE status='queued'`, atomically claims
via compare-and-swap (`UPDATE ... WHERE status='queued'`), runs through
`OrchestratorFactory` → `StatusWriter` → LangGraph pipeline.

**Key behaviors:**
- **Atomic pickup** — prevents double-execution even with multiple workers
- **Concurrency control** — `MAX_CONCURRENT_TASKS` (default 3) via ThreadPoolExecutor
- **Graceful shutdown** — SIGINT/SIGTERM waits for in-flight tasks, re-queues incomplete
- **Stale task recovery** — on startup, re-queues tasks stuck in 'running' > 30 min
- **Heartbeat** — writes `/tmp/fleet-worker-heartbeat` for Docker healthcheck
- **Worktree cleanup** — always in `finally` block after task execution
- **Cancellation** — StatusWriter checks `tasks.status` before each stage boundary
