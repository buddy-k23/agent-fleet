# Agent Fleet — Claude Instructions

## Project Overview

Multi-model AI agent orchestration platform. Submits coding tasks, coordinates
specialized agents (Architect, Backend Dev, Frontend Dev, Reviewer, Tester),
evaluates quality gates, and produces PRs. Built on LangGraph + LiteLLM + FastAPI.

**Stack:** Python 3.12+, LangGraph, LiteLLM, FastAPI, Typer, SQLAlchemy + Alembic
**Directory:** `src/agent_fleet/` (core), `cli/` (CLI client), `fleet-ui/` (React UI, future)

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
   No module-level mutable variables.

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

Scope is the module: `orchestrator`, `agents`, `api`, `cli`, `tools`, `workspace`, `store`.
Always reference the issue number: `feat(agents): add registry (#7)`

---

## Key Directories

| Path | Purpose |
|------|---------|
| `src/agent_fleet/core/` | LangGraph orchestrator, state, gates, routing |
| `src/agent_fleet/agents/` | Agent runner, registry, base interface |
| `src/agent_fleet/tools/` | Tool implementations (code, browser, shell, etc.) |
| `src/agent_fleet/api/` | FastAPI routes, schemas, websocket |
| `src/agent_fleet/models/` | LiteLLM provider wrapper, model config |
| `src/agent_fleet/workspace/` | Git worktree management |
| `src/agent_fleet/store/` | Database, persistence |
| `config/agents/` | Agent YAML definitions |
| `config/workflows/` | Workflow YAML definitions |
| `cli/` | Typer CLI client |
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

---

## Supabase Integration

**Backend data layer** — auth, database, realtime, storage all via Supabase.

### Environment Variables

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=sb_publishable_...      # Client-side (React UI)
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...   # Server-side (FastAPI)
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

- **Never bypass RLS** — always use anon key for user-scoped queries
- **Service role key** — only for admin operations (seed script, migrations)
- **Realtime** — enabled on tasks, executions, events tables
- **Storage** — `task-outputs` and `task-logs` buckets for agent artifacts
- **Seed data** — `python scripts/seed_supabase.py <user_id>` for default agents/workflows
