# End-to-End User Guide — Design Spec

**Date:** 2026-03-24
**Status:** Approved

---

## Purpose

Create a single, layered end-to-end user guide (`docs/user-guide.md`) that serves three audiences: non-technical users, developers, and operations engineers. The guide walks through the complete task lifecycle (login → submit → monitor → PR) with targeted callouts for ops and dev specifics.

## Format Decisions

| Decision | Choice |
|----------|--------|
| Format | Single doc, layered with callouts |
| Primary path | UI walkthrough |
| CLI coverage | Appendix section for power users |
| Screenshots | Placeholder image references (`![alt](screenshots/X.png)`) |
| Callout style | `> **Ops Note:**` and `> **Developer Tip:**` blockquotes |

## Document Structure

### 1. What is Agent Fleet?

One paragraph overview. What it does (submits coding tasks, orchestrates AI agents through quality gates, produces PRs), who it's for (teams that want AI-assisted development with guardrails). 2-3 sentences max.

### 2. Quick Start

Minimal steps to see value — login through first completed task. ~10 numbered steps:

1. Open the UI (`http://localhost:3001`)
2. Sign up / Log in
3. Navigate to Submit Task
4. Enter a repo path and task description
5. Select a workflow
6. Click Submit
7. Watch the Dashboard for status updates
8. Click into the task to see stage-by-stage progress
9. When complete, find the PR URL in the results
10. Review and merge the PR

Each step gets a screenshot placeholder. No deep explanations — those come in later sections.

### 3. Core Concepts

Brief explainers for the five key concepts, with a relationship diagram placeholder:

- **Tasks** — A unit of work: "Add pagination to the users API." Has a status lifecycle (queued → running → completed/error/cancelled).
- **Workflows** — A pipeline template defining which agents run in what order. Examples: "Two-Stage PoC" (plan → implement), "Default" (plan → implement → review → test → integrate).
- **Stages** — Individual steps within a workflow. Each stage runs one agent. Stages can depend on other stages (DAG).
- **Agents** — Specialized AI personas (Architect, Backend Dev, Reviewer, Tester). Each has a system prompt, tool access, and model assignment.
- **Gates** — Quality checkpoints between stages. Types: automated (run tests), score (LLM review score), approval (human sign-off).

> **Ops Note:** Agent and workflow configs are stored in Supabase (editable via UI) and also available as YAML files in `config/agents/` and `config/workflows/` for version control.

### 4. Submitting a Task

Step-by-step walkthrough of the Submit Task page:

**Fields:**
- **Repository** — local path or Git URL of the codebase to work on
- **Description** — natural language description of what to build/fix. Be specific — this is the agent's only instruction.
- **Workflow** — dropdown of available pipelines. Explain when to use each (two-stage for quick tasks, default for full review cycle).
- **Project** (optional) — group related tasks under a project

**What happens after Submit:**
1. UI sends `POST /api/v1/tasks` to the API
2. API validates and inserts a row with `status: queued`
3. Worker picks it up within 3 seconds (poll interval)
4. Status changes to `running` — visible immediately in Dashboard

> **Developer Tip:** You can also submit via API directly:
> ```bash
> curl -X POST http://localhost:8000/api/v1/tasks \
>   -H "Authorization: Bearer $TOKEN" \
>   -H "Content-Type: application/json" \
>   -d '{"repo": "/path/to/repo", "description": "Add pagination", "workflow_id": "wf-uuid"}'
> ```

Screenshot placeholders: Submit form (empty), Submit form (filled), success redirect.

### 5. Monitoring Progress

**Dashboard view:**
- Task list with status badges (queued=gray, running=blue, completed=green, error=red, cancelled=yellow)
- Click any task to open Task Monitor
- Realtime updates — no page refresh needed

**Task Monitor view:**
- Stage pipeline visualization — which stages are done, which is running, which are pending
- Execution timeline — when each stage started/finished, tokens used, cost
- Gate results — pass/fail for each quality check
- Event log — chronological record of every action

**Status meanings:**
| Status | Meaning | User Action |
|--------|---------|-------------|
| queued | Waiting for worker pickup | Wait (~3s) |
| running | Agent actively working | Monitor progress |
| completed | All stages passed, PR ready | Review the PR |
| error | Something failed | Check error message, re-submit |
| cancelled | User cancelled | Re-submit if needed |

> **Ops Note:** If tasks stay in "queued" for more than 10 seconds, the worker process may not be running. Check `docker compose logs worker` or run `python -m agent_fleet.worker` manually.

Screenshot placeholders: Dashboard with mixed statuses, Task Monitor mid-execution, completed task with PR URL.

### 6. Understanding Results

**Success path:**
- Pipeline completes → `pr_url` field is set
- Click the PR link to review on GitHub
- The PR contains all changes from all stages, with a generated description
- Review, request changes, or merge as normal

**Gate failures:**
- Automated gate fails → agent retries automatically (up to `max_retries`)
- Score gate fails → task may route back to a previous stage for revision
- If all retries exhausted → task errors with details about what failed

**Stage errors:**
- Check the error message in Task Monitor
- Common causes: missing API keys, repo not accessible, LLM rate limits
- Fix the underlying issue and re-submit the task

**Cancelling a task:**
- From Task Monitor: click Cancel button
- Cancellation takes effect at the next stage boundary (in-flight LLM calls finish)
- Worktrees are cleaned up automatically

> **Developer Tip:** Cancel via API: `DELETE /api/v1/tasks/{id}/cancel`

### 7. Managing Agents & Workflows

**Viewing agents:**
- Settings page lists all available agents
- Each shows: name, description, capabilities, default model
- Built-in agents: Architect, Backend Dev, Frontend Dev, Reviewer, Tester, plus specialized agents (DBA, Security Reviewer, Compliance Checker)

**Viewing workflows:**
- Settings page lists available workflows
- Each shows: name, stages, concurrency setting, cost limit

> **Developer Tip:** Create custom agents by adding YAML to `config/agents/` or via the Supabase `agents` table. Required fields: name, description, capabilities, tools, default_model, system_prompt.

> **Ops Note:** Run `python scripts/seed_supabase.py <user_id>` to populate default agents and workflows for a new user.

### 8. Settings & API Keys

**API Keys page:**
- Add keys for LLM providers: Anthropic, OpenAI, Google, Ollama
- Keys are encrypted at rest (Fernet)
- Test button verifies the key works
- At least one key required for the worker to execute tasks

**Profile:**
- Display name, default workflow preference

Screenshot placeholders: API Keys page, Add Key modal.

### 9. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Task stuck in "queued" | Worker not running | Start worker: `python -m agent_fleet.worker` or `docker compose up worker` |
| Task errors immediately | Missing LLM API key | Add key in Settings → API Keys |
| Task errors with "workflow not found" | Invalid workflow_id | Check workflow exists in Settings |
| UI not updating in realtime | Supabase Realtime disconnected | Refresh the page; check Supabase is running |
| "Supabase not configured" error | Missing env vars | Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` |
| Task stuck in "running" > 30 min | Agent timeout or crash | Worker auto-recovers on restart; re-queue happens automatically |

> **Ops Note:** Check worker health: `python -m agent_fleet.worker --health`. Check Docker: `docker compose ps` and `docker compose logs worker --tail 50`.

### 10. CLI Alternative (Appendix)

For power users and automation:

```bash
# Submit a task
fleet run --repo /path/to/repo --task "Add pagination to users API"

# Check status
fleet status <task-id>

# List available agents
fleet agents list

# Watch task progress
fleet status <task-id> --watch
```

**When to use CLI over UI:**
- CI/CD pipelines
- Scripting batch submissions
- Headless server environments
- Quick one-off tasks from the terminal

### 11. Operations Guide (Appendix)

**Architecture:**
Three processes share one Supabase database:
- `uvicorn` (port 8000) — API server, auth, CRUD
- `python -m agent_fleet.worker` — task execution, LLM calls
- React UI (port 3001) — user interface, Supabase Realtime

**Deployment (Docker Compose):**
```bash
docker compose up        # all 3 services
docker compose up -d     # detached
docker compose logs -f   # follow logs
```

**Environment variables:**

| Variable | Service | Required | Default |
|----------|---------|----------|---------|
| `SUPABASE_URL` | API + Worker | Yes | — |
| `SUPABASE_ANON_KEY` | API | Yes | — |
| `SUPABASE_SERVICE_ROLE_KEY` | Worker | Yes | — |
| `ANTHROPIC_API_KEY` | Worker | Yes (one LLM key) | — |
| `OPENAI_API_KEY` | Worker | Optional | — |
| `MAX_CONCURRENT_TASKS` | Worker | No | 3 |
| `POLL_INTERVAL_SECONDS` | Worker | No | 3 |

**Worker tuning:**
- `MAX_CONCURRENT_TASKS` — number of tasks running in parallel. Increase for more throughput, decrease to limit LLM cost.
- `POLL_INTERVAL_SECONDS` — how often worker checks for new tasks. 3s is a good default; increase for less Supabase load.

**Health checks:**
- Worker: `python -m agent_fleet.worker --health` (checks heartbeat file, fails if stale > 30s)
- Docker healthcheck runs every 15s automatically
- API: `GET /api/v1/health`

**Recovery:**
- Worker restart auto-recovers stale tasks (running > 30 min → re-queued)
- Worktrees cleaned up in `finally` blocks; stale GC on startup removes orphans > 24h
- Graceful shutdown (SIGINT/SIGTERM) waits for in-flight tasks, re-queues incomplete

**Scaling (future):**
- Multiple workers can run concurrently — atomic pickup prevents double-execution
- For high-throughput: use `FOR UPDATE SKIP LOCKED` (future enhancement)
- Each worker is stateless — add more containers to scale horizontally

---

## File Location

`docs/user-guide.md`

## Screenshot Placeholders

The guide includes `![alt](screenshots/X.png)` references for:
- Login page
- Submit Task form (empty + filled)
- Dashboard with mixed statuses
- Task Monitor mid-execution
- Task Monitor completed with PR URL
- API Keys page
- Add Key modal

These should be captured from a running instance and placed in `docs/screenshots/`.
