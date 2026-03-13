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

4. **Tools are sandboxed** — Shell commands run in restricted scope. File operations are confined to the task's git worktree. Browser tools run in headless Playwright. Never give agents unrestricted system access.

5. **Worktree isolation** — Each agent task runs in its own git worktree. Agents never modify the main working tree. Merges happen only after gates pass.

6. **Event-sourced state** — Every agent action and environment observation is an append-only event. Enables full replay, debugging, and audit trails.

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
name: string           # Display name
description: string    # What this agent does (used by classifier for routing)
capabilities: [string] # What it can do (code_analysis, testing, review, etc.)
tools: [string]        # Tool categories: code, browser, search, shell, api
default_model: string  # LiteLLM model identifier
system_prompt: string  # Base system prompt for the agent
max_retries: int       # Max retry attempts on gate failure (default: 2)
timeout_minutes: int   # Max execution time (default: 30)
```

### Agent-as-Tool Pattern

Agents can invoke other agents as tools, supervised by the Orchestrator. For example, the Architect agent can delegate a subtask to the Backend Dev agent. The Orchestrator maintains global context while each agent only sees its own conversation history.

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

Custom tools can be registered and assigned to agents.

---

## Workflow System

### Workflow YAML Schema

```yaml
name: string
stages:
  - name: string             # Stage identifier
    agent: string            # References agent YAML name
    model: string            # Optional model override
    depends_on: string|list  # Stage(s) that must complete first
    parallel_with: string    # Stage to run concurrently with
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
| **score** | Agent produces a numeric score. Compare against `min_score` |
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
6. Intent classifier analyzes task to validate/adjust agent routing

### Phase 3 — Stage Execution (repeats per stage)
7. Orchestrator resolves next stage (respects `depends_on`, `parallel_with`)
8. Looks up agent from registry, resolves model (stage override → agent default)
9. Creates git worktree for this agent's work
10. Agent Runner spins up: LiteLLM client + tools + system prompt + task context
11. Agent does its work — all actions/observations logged to event log
12. Agent returns output → Orchestrator evaluates the gate

### Phase 4 — Gate Evaluation
13. Gate runs checks (test suite, lint, score threshold, etc.)
14. **Pass** → merge worktree into base branch, advance to next stage
15. **Fail** → check retry count. Under limit → re-run agent with failure context + event history. Over limit → `on_fail` action (route back, halt, notify human)
16. **Reactions** fire for specific events (CI failure, review comments)

### Phase 5 — Delivery
17. All stages pass → Integrator agent merges all work, resolves conflicts
18. Creates PR via GitHub API with summary of what each agent did
19. Task marked `completed`, user notified

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
├── cli/                           # CLI client
│   ├── __init__.py
│   └── main.py                    # Typer commands
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
| State store | SQLite → PostgreSQL | Start simple, scale later |
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
