# Architecture Guide

## System Overview

```mermaid
graph TB
    CLI[CLI] --> API[FastAPI]
    UI[React UI] --> API
    UI --> SB[(Supabase)]
    API --> ORCH[LangGraph Orchestrator]
    ORCH --> RUNNER[AgentRunner]
    RUNNER --> LLM[LLM via LiteLLM]
    RUNNER --> TOOLS[Tools: code, shell]
    RUNNER --> WT[Git Worktrees]
    ORCH --> SB
```

## Orchestrator State Machine

```mermaid
stateDiagram-v2
    [*] --> route_next
    route_next --> execute_stage: stages ready
    route_next --> [*]: all done → completed
    execute_stage --> evaluate_gate
    evaluate_gate --> route_next: gate passed
    evaluate_gate --> route_next: gate failed (retry)
    evaluate_gate --> [*]: max retries → error
```

## Agent ReAct Loop

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant R as AgentRunner
    participant L as LLM
    participant T as Tools

    O->>R: run(config, context, worktree)
    loop max_iterations
        R->>L: complete(messages + tools)
        alt tool_calls
            L-->>R: tool_calls
            R->>T: execute(tool, args)
            T-->>R: result
            R->>R: append tool result
        else final answer
            L-->>R: text response
            R-->>O: AgentResult
        end
    end
```

## Pipeline Flow

```mermaid
graph LR
    P[plan<br/>Architect] --> B[backend<br/>Backend Dev]
    P --> F[frontend<br/>Frontend Dev]
    B --> R[review<br/>Reviewer]
    F --> R
    R -->|score ≥ 80| E[e2e<br/>Tester]
    R -->|score < 80<br/>route_to| B
    E --> D[deliver<br/>Integrator]
```

## Auth Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as React UI
    participant SB as Supabase Auth
    participant API as FastAPI

    U->>UI: email + password
    UI->>SB: signInWithPassword()
    SB-->>UI: JWT token
    UI->>API: GET /api/v1/agents (Bearer token)
    API->>SB: validate JWT
    SB-->>API: user_id
    API-->>UI: user's agents (RLS filtered)
```

## Data Flow

```mermaid
graph TB
    SUBMIT[Submit Task] --> DB[(Supabase tasks table)]
    DB --> ORCH[Orchestrator picks up task]
    ORCH --> WT[Create git worktree]
    WT --> AGENT[AgentRunner executes]
    AGENT --> GATE{Gate evaluation}
    GATE -->|pass| MERGE[Merge worktree]
    GATE -->|fail| RETRY[Retry with feedback]
    MERGE --> NEXT[Next stage]
    NEXT --> PR[Create PR / Summary]
    PR --> DB
    DB -->|Realtime| UI[UI updates live]
```

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Orchestrator | LangGraph | Conditional edges, checkpointing, parallel branches |
| LLM access | LiteLLM | 100+ models, unified API, no vendor lock-in |
| Agent pattern | ReAct loop | Standard for coding agents (OpenHands, SWE-agent) |
| Isolation | Git worktrees | Lightweight, no Docker overhead, real git history |
| Database | Supabase | Auth + DB + Realtime + Storage in one |
| Score gate | Reviewer JSON | Agent specifies route_to target, not hardcoded |
