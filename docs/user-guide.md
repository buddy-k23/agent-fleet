# Agent Fleet — End-to-End User Guide

Agent Fleet is a multi-model AI agent orchestration platform. You submit a coding task, it coordinates specialized AI agents (Architect, Backend Dev, Reviewer, Tester) through quality gates, and delivers a pull request. Think of it as an AI development team that plans, implements, reviews, and tests code changes for you.

---

## Quick Start

Get from zero to your first AI-generated PR in 10 steps.

**1. Open the UI**

Navigate to `http://localhost:3001` (or your deployment URL).

![Login page](screenshots/login.png)

**2. Sign up or log in**

Create an account with email/password. Authentication is handled by Supabase Auth.

**3. Add an API key**

Go to **Settings > API Keys** and add at least one LLM provider key (Anthropic or OpenAI). The worker needs this to run agents.

![API Keys page](screenshots/api-keys.png)

**4. Navigate to Submit Task**

Click **Submit Task** in the sidebar.

**5. Fill in the form**

- **Repository**: path to the codebase (e.g., `/home/user/my-project` or a Git URL)
- **Description**: what you want built or fixed — be specific
- **Workflow**: select a pipeline (start with "Two-Stage Proof of Concept")

![Submit Task form](screenshots/submit-task-filled.png)

**6. Click Submit**

The task is created with status `queued`. You're redirected to the Task Monitor.

**7. Watch the Dashboard**

The Dashboard shows all your tasks with live status updates. No page refresh needed.

![Dashboard with tasks](screenshots/dashboard.png)

**8. Monitor stage progress**

Click into your task to see the Task Monitor — stage-by-stage progress, execution timeline, gate results.

![Task Monitor running](screenshots/task-monitor-running.png)

**9. Task completes**

When all stages pass their gates, the task status changes to `completed` and a PR URL appears.

![Task Monitor completed](screenshots/task-monitor-completed.png)

**10. Review and merge the PR**

Click the PR link to review on GitHub. The PR includes all changes with a generated description. Review, request changes, or merge as usual.

---

## Core Concepts

Agent Fleet has five key concepts that work together:

**Tasks** are units of work: "Add pagination to the users API" or "Fix the login redirect bug." Each task has a status lifecycle: `queued` → `running` → `completed` (or `error` / `cancelled`).

**Workflows** are pipeline templates that define which agents run in what order. For example, the "Default" workflow runs: plan → implement (backend + frontend in parallel) → review → test → integrate. The "Two-Stage PoC" workflow is simpler: plan → implement.

**Stages** are individual steps within a workflow. Each stage runs one agent and can depend on other stages (forming a DAG). Stages with no dependencies on each other can run in parallel.

**Agents** are specialized AI personas. Each has a system prompt, tool access (code editing, shell commands, browser), and a default LLM model. Built-in agents include Architect, Backend Dev, Frontend Dev, Reviewer, Tester, DBA, Security Reviewer, and more.

**Gates** are quality checkpoints between stages. When a stage completes, its gate evaluates the output:
- **Automated** — runs checks like `tests_pass`
- **Score** — an LLM reviewer scores the output against criteria
- **Approval** — waits for human sign-off

If a gate fails, the agent retries automatically (up to `max_retries`).

> **Ops Note:** Agent and workflow configs are stored in Supabase (editable via the UI) and also available as YAML files in `config/agents/` and `config/workflows/` for version control.

---

## Submitting a Task

### The Submit Form

![Submit Task form empty](screenshots/submit-task-empty.png)

| Field | Description | Example |
|-------|-------------|---------|
| **Repository** | Path or URL of the codebase to work on | `/home/user/my-project` |
| **Description** | Natural language task description — be specific | "Add cursor-based pagination to GET /api/users with limit/offset params, update tests" |
| **Workflow** | Pipeline to use | "Two-Stage Proof of Concept" for quick tasks, "Default" for full review cycle |
| **Project** (optional) | Group related tasks together | "Q2 API improvements" |

### Writing Good Descriptions

The description is the agent's primary instruction. Better descriptions produce better results:

- **Too vague:** "Fix the API"
- **Good:** "Fix the 500 error on GET /api/users when the database connection pool is exhausted. Add connection retry logic with exponential backoff."
- **Great:** "Fix the 500 error on GET /api/users when the database connection pool is exhausted. Add connection retry logic with exponential backoff (max 3 retries, starting at 100ms). Add a unit test that simulates pool exhaustion."

### What Happens After Submit

1. The UI sends `POST /api/v1/tasks` to the API server
2. The API validates your input and creates a task row with `status: queued`
3. The fleet-worker process picks it up within ~3 seconds
4. Status changes to `running` — visible immediately on the Dashboard
5. The worker loads the workflow and agent configs, builds the LangGraph pipeline, and starts executing stages

> **Developer Tip:** Submit via API directly:
> ```bash
> curl -X POST http://localhost:8000/api/v1/tasks \
>   -H "Authorization: Bearer $TOKEN" \
>   -H "Content-Type: application/json" \
>   -d '{"repo": "/path/to/repo", "description": "Add pagination", "workflow_id": "wf-uuid"}'
> ```

---

## Monitoring Progress

### Dashboard

The Dashboard is your home screen — it shows all your tasks with live status badges.

![Dashboard](screenshots/dashboard-mixed.png)

| Status | Badge | Meaning |
|--------|-------|---------|
| `queued` | Gray | Waiting for worker pickup (~3s) |
| `running` | Blue | Agent actively working |
| `completed` | Green | All stages passed, PR ready |
| `error` | Red | Something failed — check error message |
| `cancelled` | Yellow | You cancelled the task |

Click any task to open the Task Monitor.

### Task Monitor

The Task Monitor shows detailed progress for a single task:

![Task Monitor](screenshots/task-monitor-detail.png)

**Pipeline visualization** — see which stages are complete (green), running (blue), pending (gray), or failed (red).

**Execution timeline** — when each stage started and finished, tokens consumed, estimated cost.

**Gate results** — pass/fail for each quality checkpoint, with details on what was checked.

**Event log** — chronological record of every action: routing decisions, stage starts/stops, gate evaluations, errors.

Updates appear in realtime via Supabase Realtime — no page refresh needed.

> **Ops Note:** If the UI stops updating, check that Supabase is running and the Realtime connection is active. A page refresh re-establishes the subscription.

---

## Understanding Results

### Success: PR Ready

When all stages complete and pass their gates:

1. The task status changes to `completed`
2. A **PR URL** appears in the Task Monitor
3. Click it to review on GitHub (or your Git provider)
4. The PR contains all code changes from all stages, with a generated description summarizing what was done and why

Review the PR as you would any developer's work — request changes, approve, or merge.

### Gate Failures

Gates are quality checkpoints. When one fails:

- **Automated gate** (e.g., tests_pass) — the agent retries automatically, up to `max_retries` (default: 2). You'll see retry attempts in the execution timeline.
- **Score gate** — if the reviewer scores below `min_score`, the task may route back to a previous stage for revision (e.g., reviewer sends work back to the developer).
- **Approval gate** — the task pauses at `awaiting_approval`. You approve or reject from the Task Monitor.

If all retries are exhausted, the task status changes to `error` with a message explaining what failed.

### Stage Errors

If a stage errors out:

1. Check the **error message** in the Task Monitor
2. Common causes:
   - Missing API key (add one in Settings > API Keys)
   - Repository path not accessible to the worker
   - LLM rate limit hit (wait and re-submit)
   - Agent timeout (task took longer than `timeout_minutes`)
3. Fix the underlying issue and submit a new task

### Cancelling a Task

You can cancel a `queued` or `running` task:

- In the Task Monitor, click the **Cancel** button
- Cancellation takes effect at the next stage boundary — in-flight LLM calls finish their current request
- Worktrees are cleaned up automatically

> **Developer Tip:** Cancel via API: `DELETE /api/v1/tasks/{id}/cancel`

---

## Managing Agents & Workflows

### Viewing Agents

The Settings page lists all available agents. Each shows:

- **Name** — e.g., "Architect", "Backend Dev"
- **Description** — what the agent specializes in
- **Capabilities** — code_analysis, testing, review, etc.
- **Default model** — which LLM it uses (e.g., `anthropic/claude-opus-4-6`)
- **Tools** — what it can do: edit code, run shell commands, search, browse

Built-in agents: Architect, Backend Dev, Frontend Dev, Reviewer, Tester, DBA, Security Reviewer, Compliance Checker, Impact Analyzer, Integrator.

### Viewing Workflows

The Settings page also lists available workflows:

- **Name** — e.g., "Default", "Two-Stage Proof of Concept"
- **Stages** — ordered list of stages with their agents and gates
- **Concurrency** — max parallel tasks per repo
- **Cost limit** — kill switch if cost exceeds threshold

### Choosing the Right Workflow

| Workflow | Best for | Stages |
|----------|----------|--------|
| Two-Stage PoC | Quick tasks, experiments | plan → implement |
| Default | Production work | plan → implement (parallel) → review → test → integrate |
| Banking Standard | Regulated environments | plan → implement → security review → compliance → test → integrate |

> **Developer Tip:** Create custom agents by adding YAML to `config/agents/` or via the Supabase `agents` table. Required fields: `name`, `description`, `capabilities`, `tools`, `default_model`, `system_prompt`.

> **Ops Note:** Run `python scripts/seed_supabase.py <user_id>` to populate default agents and workflows for a new user account.

---

## Settings & API Keys

### API Keys

Navigate to **Settings > API Keys** to manage LLM provider credentials.

![API Keys page](screenshots/api-keys-page.png)

**Adding a key:**
1. Click "Add Key"
2. Select provider: Anthropic, OpenAI, Google, or Ollama
3. Paste your API key
4. Optionally add a label
5. Click Save

Keys are encrypted at rest using Fernet encryption. The UI displays masked versions (e.g., `sk-***...QwAA`).

**Testing a key:** Click the "Test" button next to any key. It makes a small API call to verify the key is valid and the provider is reachable.

**At least one working API key is required** for the worker to execute tasks. Without one, tasks will error immediately.

### Profile

- **Display name** — shown in the UI
- **Default workflow** — pre-selected when submitting tasks

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| Task stuck in "queued" | Worker not running | `python -m agent_fleet.worker` or `docker compose up worker` |
| Task errors immediately | Missing LLM API key | Add a key in Settings > API Keys |
| Task errors with "workflow not found" | Invalid workflow_id | Verify the workflow exists in Settings; re-seed if needed |
| UI not updating in realtime | Supabase Realtime disconnected | Refresh the page; check Supabase is running |
| "Supabase not configured" error | Missing environment variables | Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `.env` |
| Task stuck in "running" > 30 min | Agent timeout or crash | Worker auto-recovers on restart — stale tasks are re-queued |
| "Rate limit" errors | LLM provider throttling | Wait 1-2 minutes and re-submit; or add a second provider key |
| PR not created | Integrator stage failed | Check if repo has a remote; check Git credentials |

> **Ops Note:** Diagnostic commands:
> ```bash
> # Check worker health
> python -m agent_fleet.worker --health
>
> # Check Docker services
> docker compose ps
>
> # Worker logs
> docker compose logs worker --tail 50
>
> # API health
> curl http://localhost:8000/api/v1/health
> ```

---

## Appendix A: CLI Alternative

For power users who prefer the terminal, Agent Fleet has a full CLI.

### Submitting a Task

```bash
fleet run --repo /path/to/repo --task "Add pagination to the users API"
```

### Checking Status

```bash
# One-time check
fleet status <task-id>

# Watch mode (updates until complete)
fleet status <task-id> --watch
```

### Listing Agents

```bash
fleet agents list
```

### When to Use CLI Over UI

- **CI/CD pipelines** — trigger tasks from automated workflows
- **Batch submissions** — script multiple task submissions
- **Headless servers** — no browser available
- **Quick one-offs** — faster than opening the UI for a single task

---

## Appendix B: Operations Guide

### Architecture

Agent Fleet runs as three processes sharing one Supabase database:

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

- **API server** (`uvicorn`, port 8000) — handles auth, CRUD, WebSocket chat
- **Worker** (`python -m agent_fleet.worker`) — task execution, LLM calls, quality gates
- **UI** (Vite/React, port 3001) — user interface, Supabase Realtime subscriptions

### Deployment

**Docker Compose (recommended):**

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Restart worker only
docker compose restart worker

# Stop everything
docker compose down
```

**Manual (development):**

```bash
# Terminal 1: API
uvicorn agent_fleet.main:app --reload --port 8000

# Terminal 2: Worker
python -m agent_fleet.worker

# Terminal 3: UI
cd fleet-ui && npm run dev
```

### Environment Variables

| Variable | Service | Required | Default | Description |
|----------|---------|----------|---------|-------------|
| `SUPABASE_URL` | API + Worker | Yes | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | API | Yes | — | Public key, RLS enforced |
| `SUPABASE_SERVICE_ROLE_KEY` | Worker | Yes | — | Admin key, bypasses RLS |
| `ANTHROPIC_API_KEY` | Worker | One LLM key required | — | Anthropic API key |
| `OPENAI_API_KEY` | Worker | Optional | — | OpenAI API key |
| `MAX_CONCURRENT_TASKS` | Worker | No | `3` | Max parallel tasks |
| `POLL_INTERVAL_SECONDS` | Worker | No | `3` | Seconds between polls |

### Worker Tuning

- **`MAX_CONCURRENT_TASKS`** — number of tasks running simultaneously. Higher = more throughput but more LLM cost and CPU. Start with 3, increase based on load.
- **`POLL_INTERVAL_SECONDS`** — how often the worker checks for new tasks. 3s is barely perceptible for users; increase to 10-30s to reduce Supabase query load in production.

### Health Checks

| Check | Command | Healthy |
|-------|---------|---------|
| Worker | `python -m agent_fleet.worker --health` | Heartbeat < 30s old |
| API | `GET /api/v1/health` | `{"status": "ok"}` |
| Docker | `docker compose ps` | All services `Up (healthy)` |

The worker writes a heartbeat file (`/tmp/fleet-worker-heartbeat`) every poll cycle. The Docker healthcheck reads this file every 15 seconds and restarts the container if stale.

### Recovery

**Stale task recovery:** On startup, the worker scans for tasks stuck in `running` longer than 30 minutes and re-queues them. This handles crashes, OOM kills, and ungraceful shutdowns.

**Worktree cleanup:** Each task's git worktrees are cleaned up in a `finally` block after execution. On startup, a GC sweep removes orphaned worktrees older than 24 hours.

**Graceful shutdown:** SIGINT/SIGTERM signals the worker to stop polling. It waits for in-flight tasks to complete (up to 5 minutes), then re-queues anything still running.

### Scaling

The current architecture supports horizontal scaling:

- **Multiple workers** can run concurrently — atomic pickup (compare-and-swap on `status='queued'`) prevents double-execution
- Workers are stateless — add more containers to increase throughput
- **Future enhancement:** `FOR UPDATE SKIP LOCKED` for advisory lock-based pickup under high contention

### Monitoring

Key metrics to watch:

- **Tasks in "queued" state** — if growing, add more workers or increase `MAX_CONCURRENT_TASKS`
- **Task error rate** — high errors may indicate missing API keys, bad configs, or LLM issues
- **Worker heartbeat staleness** — if > 30s, worker is stuck or dead
- **Supabase connection count** — each worker holds persistent connections; monitor pool usage
