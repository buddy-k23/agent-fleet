# Agent Fleet — Design Specification

## Overview

Multi-model AI agent orchestration platform for coding projects. Teams submit tasks (issues, feature requests, bug fixes), and a fleet of specialized agents collaborates through quality gates to produce pull requests. Built on LangGraph + LiteLLM + FastAPI.

**Primary use cases:**
- Personal tool for managing coding projects (e.g., fabric-platform)
- General-purpose platform teams can self-service — define agents, workflows, and model preferences

**Key design influences:**
- Composio Agent Orchestrator — parallel agents, git worktree isolation, plugin architecture, CI-fail reactions
- AWS Agent Squad — intent classifier routing, agents-as-tools, supervisor pattern, global context with local history
- OpenHands — event-sourced state, sandboxed execution, model-agnostic SDK
- LangGraph — conditional edges, parallel branches, human-in-the-loop, checkpointing

---

## Architecture

### 5 Layers

```
CLI (Typer)  →  REST API (FastAPI)  →  Orchestrator (LangGraph)  →  Agent Pool  →  Codebase (git worktrees)
                                              ↕
                                     Agent Registry (YAML)
                                     Workflow Config (YAML)
                                     Event Log (append-only)
                                     State Store (SQLite → Postgres)
```

### Core Components

| Component | Responsibility |
|-----------|---------------|
| **CLI** | User-facing commands: `fleet run`, `fleet agents list`, `fleet status` |
| **API** | REST endpoints for task submission, status, agent management. WebSocket for real-time streaming. |
| **Orchestrator** | LangGraph state graph — routes tasks to agents, evaluates gates, handles retries. Contains an intent classifier for intelligent routing. |
| **Agent Registry** | YAML definitions of available agents — name, capabilities, default model, tools |
| **Workflow Config** | Per-project YAML defining pipeline stages, agent assignments, gate criteria, reactions |
| **Agent Runner** | Executes an agent — sets up LLM via LiteLLM, injects tools, runs in a git worktree. Runtime is pluggable (swappable agent backends). |
| **Event Log** | Append-only log of every agent action and observation. Enables replay, debugging, and audit. |
| **State Store** | Tracks task status, agent outputs, gate results, execution history. SQLite for v1, Postgres for production. |
| **Intent Classifier** | LLM-based classifier that analyzes task content and routes to the best agent. Supplements static workflow config with intelligent routing. |

---

## Architecture Principles

1. **Orchestrator owns the flow** — All task routing, retries, and gate evaluation go through the LangGraph orchestrator. Agents never call other agents directly. Hub-and-spoke, evolving toward hybrid (agents emit events for observability).

2. **Agents are config, not code** — Adding a new agent means adding a YAML file to `config/agents/`. No Python code changes required.

3. **LiteLLM for all model calls** — Never import openai, anthropic, or google SDKs directly. All LLM calls go through LiteLLM so any model (cloud or local) works with zero code changes.

4. **Tools are sandboxed** — In v1, sandboxing is path-based: file operations are confined to the task's git worktree (enforced by the tool layer), shell commands run with `cwd` set to the worktree, and browser tools run in headless Playwright. Agents cannot access files outside their worktree or the system's home directory. Network access is unrestricted in v1. Container-based sandboxing (chroot, seccomp, Docker) is on the backlog for hardened multi-tenant deployments.

5. **Worktree isolation** — Each agent task runs in its own git worktree. Agents never modify the main working tree. Merges happen only after gates pass. Parallel agents each get their own sub-branch off `fleet/task-{id}`. After all parallel stages pass their gates, the Integrator merges sub-branches into the task branch in deterministic order (alphabetical by stage name). Merge conflicts at this stage are handed to the Integrator agent to resolve.

6. **Event-sourced state** — Every agent action and environment observation is an append-only event stored in the Event table of the state store. Enables full replay, debugging, and audit trails.

7. **Fail-safe by default** — Every agent execution has a `timeout_minutes` kill switch and a `max_tokens` budget. Worktrees are cleaned up in `finally` blocks. Crashed tasks auto-resume from LangGraph checkpoints on API restart. Ctrl+C triggers graceful shutdown: marks task as `interrupted`, cleans up worktrees.

---

## Agent System

### Built-in Agent Roles

| Agent | Purpose | Default Tools |
|-------|---------|---------------|
| **Orchestrator** | Routes tasks, manages workflow, handles agent lifecycle | — (internal) |
| **Architect** | Analyzes codebase, designs solutions, creates implementation plans | code, search |
| **Backend Dev** | API/service/database implementation | code, shell |
| **Frontend Dev** | React/UI implementation | code, shell, browser |
| **Reviewer** | Code review, security, quality checks | code, search |
| **Tester** | Writes and runs tests | code, shell, browser |
| **Integrator** | Merges worktrees, resolves conflicts, creates PR | code, shell |

### Custom Agents

Teams register new agents by adding YAML files. Examples: DevOps agent, Docs agent, DBA agent, Web Scraper agent.

### Agent YAML Schema

```yaml
name: string             # Display name
description: string      # What this agent does (used by classifier for routing)
capabilities: [string]   # What it can do (code_analysis, testing, review, etc.)
tools: [string]          # Tool categories: code, browser, search, shell, api
default_model: string    # LiteLLM model identifier
system_prompt: string    # Base system prompt for the agent
max_retries: int         # Max retry attempts on gate failure (default: 2)
timeout_minutes: int     # Max execution time (default: 30)
max_tokens: int          # Max LLM tokens per execution (default: 100000)
can_delegate: [string]   # Agent names this agent can delegate subtasks to (default: [])
```

### Agent-as-Tool Pattern

Agents can request the Orchestrator to delegate subtasks to other agents. This is not direct agent-to-agent invocation — the requesting agent emits a `delegate` action in the event log, and the Orchestrator handles routing, worktree setup, and context scoping.

**How it works:**
1. Agent (e.g., Architect) emits a `delegate` action: `{ "target": "backend-dev", "subtask": "...", "context": "..." }`
2. Orchestrator receives the delegation request and validates it
3. Orchestrator creates a new execution for the target agent with scoped context
4. Target agent runs in its own worktree, returns output to Orchestrator
5. Orchestrator passes the result back to the requesting agent

**Guardrails:**
- `can_delegate: [agent-name, ...]` field in agent YAML explicitly lists which agents this agent can delegate to. If omitted, no delegation allowed.
- Max delegation depth of 2 (A → B → C, but C cannot delegate further) to prevent circular chains.
- The Orchestrator tracks the delegation chain and rejects any request that would create a cycle.

```yaml
# Example: Architect can delegate to backend-dev and frontend-dev
name: "Architect"
can_delegate:
  - backend-dev
  - frontend-dev
```

This preserves Principle #1 (Orchestrator owns the flow) and Principle #2 (agents are config, not code) — delegation permissions are declared in YAML, executed by the Orchestrator.

---

## Tool System

Tools are pluggable capabilities provisioned to agents based on their YAML config.

| Tool Category | Examples | Implementation |
|---------------|----------|----------------|
| **code** | File read/write, git operations, code search | Native Python (pathlib, gitpython) |
| **browser** | Navigate, click, fill forms, screenshot, scrape | Playwright |
| **search** | Web search, documentation lookup | Web search APIs |
| **shell** | Run commands, Docker, deploy scripts | asyncio.create_subprocess_exec (sandboxed) |
| **api** | HTTP requests, webhook calls | httpx |

### Custom Tools

Custom tools are Python modules that implement the `BaseTool` interface and are registered via YAML:

```yaml
# config/tools/jira.yaml
name: jira
module: agent_fleet.tools.contrib.jira   # Python module path
class: JiraTool                           # Class implementing BaseTool
config:
  base_url: ${JIRA_URL}
  api_token: ${JIRA_TOKEN}
```

The `BaseTool` interface requires: `name`, `description` (used by LLM), `execute(input) -> output`, and `schema()` (JSON schema for the tool's parameters). Custom tools are the one exception to "agents are config, not code" — tool capabilities require Python, but agents that *use* those tools are still YAML-only.

---

## Workflow System

### Workflow YAML Schema

```yaml
name: string
concurrency: int             # Max parallel tasks against the same repo (default: 1)
max_cost_usd: float          # Kill switch — halt task if estimated cost exceeds this
stages:
  - name: string             # Stage identifier
    agent: string            # References agent YAML name
    model: string            # Optional model override
    depends_on: string|list  # Stage(s) that must complete first (parallelism is inferred: stages with same depends_on run concurrently)
    gate:
      type: automated|score|approval|custom
      checks: [string]       # For automated gates
      min_score: int          # For score gates
      on_fail: retry|route_to|halt
      route_target: string   # Stage to route back to on failure
      max_retries: int        # Override agent default
    reactions:                # Auto-responses to events
      ci_failed:
        action: send_to_agent
        retries: 2
      review_comments:
        action: address_comments
    actions: [string]         # Post-gate actions (merge, create_pr, etc.)
```

### Gate Types

| Type | Behavior |
|------|----------|
| **automated** | Run checks (tests, lint, build). Pass/fail based on exit codes |
| **score** | A separate evaluator agent (typically Reviewer) produces a score 0-100 as a structured JSON field `{ "score": N, "reasoning": "..." }`. Compare against `min_score`. The evaluating agent is specified via `scored_by` field in the gate config (defaults to the `reviewer` agent). |
| **approval** | Orchestrator (or human) reviews output before proceeding |
| **custom** | Run a user-defined script or function |

### Default Pipeline

```
Task → Architect (plan) → [Backend Dev ∥ Frontend Dev] → Reviewer → Tester (E2E) → Integrator → PR
         Gate: approval     Gate: tests+lint pass       Gate: score≥80   Gate: all pass   Gate: merge clean
                                    ↑                        |
                                    └── on_fail: route_back ─┘
```

---

## End-to-End Task Flow

### Phase 1 — Submission
1. User submits task via CLI/API (e.g., `fleet run --repo ./fabric-platform --task "Implement issue #52"`)
2. API validates, creates task record (status: `queued`)
3. CLI starts polling/streaming status via WebSocket

### Phase 2 — Orchestration
4. Orchestrator picks up task, loads project's workflow config
5. Creates base branch `fleet/task-{id}`
6. Intent classifier analyzes task to suggest agent routing adjustments. Workflow config is authoritative — the classifier can recommend skipping a stage (e.g., "no frontend work needed") or adding one, but the Orchestrator logs the recommendation and follows the workflow unless `classifier_mode: override` is set. Default is `classifier_mode: suggest` (log-only). Can be disabled entirely with `classifier_mode: disabled` for deterministic pipelines.

### Phase 3 — Stage Execution (repeats per stage)
7. Orchestrator resolves next stage (respects `depends_on` — stages sharing the same dependency run in parallel automatically)
8. Looks up agent from registry, resolves model (stage override → agent default)
9. Creates git worktree for this agent's work
10. Agent Runner spins up: LiteLLM client + tools + system prompt + task context
11. Agent does its work — all actions/observations logged to event log
12. Agent returns output → Orchestrator evaluates the gate

### Phase 4 — Gate Evaluation
13. Gate runs checks (test suite, lint, score threshold, etc.)
14. **Pass** → merge worktree into base branch, advance to next stage
15. **Fail** → check retry count. Under limit → re-run agent with failure context + event history. Over limit → `on_fail` action (route back, halt, notify human)
16. **Reactions** fire for specific events (CI failure, review comments). Reactions run *after* gate evaluation completes — they do not conflict with gate `on_fail`. Gate handles the retry/routing decision; reactions handle supplementary actions (e.g., posting a comment, notifying a channel).

### Phase 5 — Delivery
17. All stages pass → Integrator agent merges all work, resolves conflicts
18. Creates PR via GitHub API with summary of what each agent did
19. Task marked `completed`, user notified

---

## Concurrency & Task Queue

- Tasks are queued and executed by a background worker loop in the API process.
- The `concurrency` field in workflow config controls max parallel tasks per repo (default: 1). Tasks for the same repo queue up; tasks for different repos run concurrently.
- Worktree names include the task ID (`fleet-worktree-{task_id}-{stage}`) to avoid collisions.
- If two tasks targeting the same repo both complete and try to create PRs, they create separate PRs on separate branches (`fleet/task-{id}`). No conflict — GitHub handles parallel PRs natively.
- Global concurrency limit configurable via `FLEET_MAX_CONCURRENT_TASKS` env var (default: 5).

---

## Error Handling & Recovery

| Failure | Behavior |
|---------|----------|
| **LLM call fails** (rate limit, network, bad key) | Retry with exponential backoff (3 attempts, 2s/8s/30s). After 3 failures, mark execution as `error`, advance to gate with failure context. |
| **Agent timeout** (`timeout_minutes` exceeded) | Kill the agent process, clean up worktree, mark execution as `timeout`. Gate evaluates as fail. |
| **Token budget exceeded** (`max_tokens`) | Agent receives a "budget exhausted" signal, must return partial output. Gate evaluates partial output. |
| **Worktree creation fails** (disk full, git lock) | Task marked as `error` with diagnostic message. No retry — requires human intervention. |
| **Orchestrator crash** | LangGraph checkpoint persists state. On API restart, incomplete tasks auto-resume from last checkpoint. |
| **CLI interrupted** (Ctrl+C) | Graceful shutdown: task marked `interrupted`, worktrees cleaned up. Task can be resumed via `fleet resume {task-id}`. |
| **Merge conflict** (parallel worktrees) | Conflict handed to the Integrator agent. If Integrator fails, task marked `needs_human` with conflict details. |
| **Cost limit exceeded** (`max_cost_usd`) | Task halted immediately, all agents stopped, worktrees preserved for inspection. Task marked `cost_limit`. |

---

## State & Persistence

### State Store Records

| Record | Fields |
|--------|--------|
| Task | id, repo, description, status, workflow, created_at |
| Execution | id, task_id, stage, agent, model, worktree_path, started_at, finished_at |
| Gate Result | id, execution_id, gate_type, passed, details (test output, score, etc.) |
| Agent Output | id, execution_id, files_changed, summary, raw_log |
| Event | id, task_id, execution_id, type (action/observation), timestamp, payload |

### LangGraph Checkpointing

Graph state is checkpointed after each node execution. Long-running tasks survive crashes and can be resumed from the last checkpoint.

---

## Model Support

All models accessed through LiteLLM unified interface.

### Cloud Models
- Anthropic: `anthropic/claude-opus-4-6`, `anthropic/claude-sonnet-4-6`, `anthropic/claude-haiku-4-5`
- OpenAI: `openai/gpt-4o`, `openai/gpt-4o-mini`
- Google: `gemini/gemini-2.5-pro`, `gemini/gemini-2.5-flash`

### Local Models
- Ollama: `ollama/llama3`, `ollama/codellama`, `ollama/deepseek-coder`
- llama.cpp: Via OpenAI-compatible API endpoint

Teams configure model per agent (in agent YAML) or per stage (in workflow YAML). Stage-level overrides take precedence.

---

## Communication Model

### Phase 1 (v1): Hub-and-Spoke
All communication goes through the Orchestrator. Agents receive task context, produce output, return to Orchestrator.

### Phase 2 (future): Hybrid
Agents emit events to a shared event bus for observability. Other agents can optionally subscribe to events. Orchestrator still owns routing and gate evaluation.

---

## Project Structure

```
agent-fleet/
├── pyproject.toml
├── CLAUDE.md
├── README.md
├── .env.example
│
├── src/
│   └── agent_fleet/
│       ├── __init__.py
│       ├── main.py                # FastAPI app entrypoint
│       │
│       ├── api/                   # REST API layer
│       │   ├── routes/
│       │   │   ├── tasks.py       # Submit, list, cancel tasks
│       │   │   ├── agents.py      # CRUD agent definitions
│       │   │   ├── workflows.py   # CRUD workflow configs
│       │   │   └── models.py      # List/configure available models
│       │   ├── schemas.py         # Pydantic request/response DTOs
│       │   └── websocket.py       # Real-time task status streaming
│       │
│       ├── core/                  # Orchestration engine
│       │   ├── orchestrator.py    # LangGraph state graph
│       │   ├── state.py           # Graph state schema
│       │   ├── gates.py           # Gate evaluation logic
│       │   ├── router.py          # Agent routing decisions
│       │   ├── classifier.py      # LLM-based intent classifier
│       │   └── events.py          # Event log (append-only)
│       │
│       ├── agents/                # Agent execution
│       │   ├── runner.py          # Spins up agent with model + tools + worktree
│       │   ├── registry.py        # Loads/validates agent YAML definitions
│       │   └── base.py            # Base agent interface
│       │
│       ├── tools/                 # Tool categories agents can use
│       │   ├── code.py            # File read/write, git ops
│       │   ├── browser.py         # Playwright-based web tools
│       │   ├── search.py          # Web search, doc lookup
│       │   ├── shell.py           # Command execution (sandboxed)
│       │   └── api.py             # HTTP requests
│       │
│       ├── models/                # LLM provider abstraction
│       │   ├── provider.py        # LiteLLM wrapper
│       │   └── config.py          # Model registry, API keys, local endpoints
│       │
│       ├── workspace/             # Codebase interaction
│       │   ├── worktree.py        # Git worktree create/merge/cleanup
│       │   └── git.py             # Git operations (branch, commit, PR)
│       │
│       └── store/                 # Persistence
│           ├── database.py        # SQLite/Postgres connection
│           ├── models.py          # Table definitions
│           └── repository.py      # Task, execution, gate result storage
│
├── config/                        # Default configs
│   ├── agents/                    # Built-in agent definitions
│   │   ├── architect.yaml
│   │   ├── backend-dev.yaml
│   │   ├── frontend-dev.yaml
│   │   ├── reviewer.yaml
│   │   ├── tester.yaml
│   │   └── integrator.yaml
│   └── workflows/
│       └── default.yaml           # Default full pipeline
│
├── cli/                           # CLI client (can invoke orchestrator directly OR call API)
│   ├── __init__.py
│   └── main.py                    # Typer commands — uses API when server is running, falls back to direct orchestrator invocation for zero-setup personal use
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
└── fleet-ui/                      # React web UI (future)
    ├── src/
    │   ├── pages/
    │   │   ├── Dashboard/         # Active tasks, agent status, metrics
    │   │   ├── AgentBuilder/      # Create/edit agents visually
    │   │   ├── WorkflowDesigner/  # Drag-drop pipeline builder
    │   │   ├── TaskMonitor/       # Real-time execution view
    │   │   ├── ProjectSettings/   # Repo config, default workflow
    │   │   └── ModelRegistry/     # Configure available models
    │   └── ...
    └── ...
```

---

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent orchestration | LangGraph | Graph-based workflows, conditional edges, checkpointing, parallel branches |
| Model abstraction | LiteLLM | Unified interface for 100+ models (cloud + local) |
| REST API | FastAPI | Async, auto-docs, Pydantic validation |
| CLI | Typer | Clean Python CLI with auto-generated help |
| State store | SQLAlchemy + Alembic (SQLite → PostgreSQL) | ORM abstracts dialect differences, Alembic manages migrations |
| Browser tools | Playwright | Already familiar, battle-tested |
| Web UI (future) | React + MUI + React Flow | Reuse fabric-platform experience |
| Logging | structlog | Structured JSON logs with context |
| Testing | pytest + pytest-cov | 80% coverage gate |
| Linting | ruff | Fast Python linter + formatter |
| Type checking | mypy | Static type analysis |

---

## Build Order

1. **Core engine** — LangGraph orchestrator, agent registry, agent runner, LiteLLM provider, gate evaluation
2. **Workspace** — Git worktree management, branch/merge/PR operations
3. **API** — FastAPI endpoints for tasks, agents, workflows, status
4. **CLI** — Typer commands wrapping the API
5. **Event log** — Append-only event store, replay capability
6. **Intent classifier** — LLM-based routing to supplement static workflow config
7. **GitHub integration** — Webhook handler for issues/PRs
8. **Web UI** — React dashboard, agent builder, workflow designer
9. **Container support** — Docker-based agent sandboxing (backlog)

---

## Backlog

- Container-based agent sandboxes (Docker)
- A2A (Agent-to-Agent) protocol support for interoperability
- Cost tracking per model per task
- Agent performance benchmarking and comparison
- Multi-repo support (monorepo and polyrepo)
- Webhook notifications (Slack, email)
- Role-based access control for teams
- Workflow templates marketplace
