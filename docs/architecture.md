# Architecture Guide

## Overview

```
CLI / React UI → FastAPI API → LangGraph Orchestrator → Agent Pool → Git Worktrees
                                      ↕
                              Supabase (Auth, DB, Realtime, Storage)
```

## Orchestrator (LangGraph)

State graph cycle: `route_next → execute_stage → evaluate_gate → (continue or end)`

- **route_next** — uses DAG Router to find ready stages, sets `current_stage`
- **execute_stage** — creates worktree, runs AgentRunner with tools, stores result
- **evaluate_gate** — runs checks (pytest), evaluates score, routes back on failure
- **Conditional edges** — route_next can end the graph, evaluate_gate can loop or end

## Agent Lifecycle (ReAct Loop)

```
Build messages (system_prompt + task_context)
    ↓
LOOP (max_iterations):
    Call LLM with messages + tool schemas
    ↓
    Tool calls? → Execute tools → Append results → Continue
    No tools?  → Return final answer
```

## Gate Types

| Type | How it works |
|------|-------------|
| **automated** | Run pytest, pass/fail on exit code |
| **score** | Parse reviewer JSON `{"score":N}`, compare vs min_score |
| **approval** | Auto-approve (human-in-the-loop planned) |
| **custom** | User-defined script |

## Parallel Execution

Stages with same `depends_on` run concurrently via `ThreadPoolExecutor`.

## Research Sources

- **Composio Agent Orchestrator** — plugin architecture, git worktree per agent, CI-fail reactions
- **AWS Agent Squad** — intent classifier, agents-as-tools, supervisor pattern
- **OpenHands** — event-sourced state, sandboxed execution, model-agnostic SDK
- **LangGraph** — conditional edges, parallel branches, checkpointing
