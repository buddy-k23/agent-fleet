# Agent Runner & End-to-End Proof of Concept — Design Specification

## Overview

Wire the Agent Runner and orchestrator to execute a real two-stage pipeline (architect → backend dev) against a test repo, calling real LLMs via LiteLLM, with an automated pytest gate. This is the proof of concept that validates the entire v1 architecture works end-to-end.

**Scope:** Two-stage pipeline (plan + backend), sequential execution, automated gate (pytest), CLI invocation, no PR creation, no parallel stages.

**Prior spec:** `docs/superpowers/specs/2026-03-13-agent-fleet-design.md`

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| First run scope | Two-stage (architect → backend dev) | Proves stage handoff without parallel complexity |
| Test target | Minimal calculator test repo | Predictable, fast, no risk to real code |
| Plan format | Markdown with conventions | Human-readable, flexible, still usable as context if parsing fails |
| Gate type | Automated — run `pytest` | Most concrete signal for PoC |
| Runner pattern | ReAct tool loop (class) | Standard coding agent pattern, multi-step tool use, testable |
| Execution | CLI direct invocation | No API server needed for PoC |

---

## Agent Runner

### ReAct Tool Loop

The Agent Runner is a class that implements a ReAct-style tool-use loop:

1. Build messages: system prompt (from YAML) + task context (from orchestrator)
2. Build tool schemas from agent's tool list, scoped to worktree
3. Call LLM via LiteLLM with messages + tool schemas
4. If LLM responds with tool calls → execute each tool, append results to messages, loop
5. If LLM responds with text (no tool calls) → return as final output
6. If token budget or max iterations exceeded → return partial result

```
AgentRunner.run(agent_config, task_context, worktree_path)
    │
    ├── Build messages: system_prompt + task_context
    ├── Instantiate tools from agent config
    │
    └── LOOP (max_iterations=20):
         ├── Call LLM with messages + tools
         ├── Response has tool_calls?
         │   ├── YES → Execute each tool → append results → continue
         │   └── NO  → Final answer → return AgentResult
         ├── Token budget exceeded? → return partial
         └── Max iterations hit? → return with warning
```

### AgentResult

```python
class AgentResult(BaseModel):
    success: bool            # False if max iterations hit or error
    output: str              # Agent's final text output
    files_changed: list[str] # From git diff --name-only in worktree after run
    tokens_used: int
    iterations: int
    tool_calls: list[dict]   # Log of all tool calls made
```

`files_changed` is populated by running `git diff --name-only` (for modified) and `git ls-files --others --exclude-standard` (for new files) in the worktree after the run completes. This is more reliable than tracking WriteFileTool calls.

### AgentRunner Constructor

```python
class AgentRunner:
    def __init__(self, provider: LLMProvider, tools: list[BaseTool], max_iterations: int = 20):
        """DI via constructor for testability. Provider and tools are injected."""
        ...

    def run(self, agent_config: AgentConfig, task_context: str, worktree_path: Path) -> AgentResult:
        """Execute the agent's ReAct loop. Returns when agent produces final text or hits limits."""
        ...
```

`max_iterations` hit → returns `AgentResult(success=False, output="Max iterations reached")`.

### Tool Instantiation

A tool registry function maps tool category names (from agent YAML) to concrete tool instances scoped to a worktree. Unknown tool categories are skipped with a warning log (handles the `search` category which has no implementation yet).

```python
def create_tools(tool_names: list[str], worktree_path: Path) -> list[BaseTool]:
    """Map tool category names to instantiated tools."""
    # "code" → [ReadFileTool, WriteFileTool, ListFilesTool]
    # "shell" → [ShellTool]
    # unknown category → log warning, skip
```

### Tool Schema Conversion to LiteLLM Format

`BaseTool.schema()` returns bare JSON Schema (the `parameters` portion). The tool registry wraps each tool into the OpenAI function-calling format that LiteLLM expects:

```python
def tool_to_litellm_schema(tool: BaseTool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.schema(),
        },
    }
```

This conversion happens in `tools/registry.py` when building the tool list.

### Tool Call Message Serialization

When the LLM responds with tool calls, the conversation history must follow the OpenAI/LiteLLM format exactly:

1. Append the assistant message as-is (contains `tool_calls` array)
2. For each tool call, execute the tool and append:
   ```python
   {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}
   ```
3. Tool call arguments are parsed via `json.loads(call.function.arguments)` with a try/except — if parsing fails, return an error message to the LLM: `"Invalid JSON arguments. Please retry with valid JSON."`
4. If the tool name is not found, return: `"Tool '{name}' not found. Available: {tool_names}"`

### LLM Provider — Tool Call Handling

The LLMProvider.complete() method needs to handle tool-call responses where `content` may be None and `tool_calls` is populated. The provider returns a new `LLMResponse` that includes the raw message (with tool calls) so the runner can process them.

```python
class LLMResponse(BaseModel):
    content: str
    model: str
    tokens_used: int
    cost_usd: float = 0.0
    tool_calls: list[dict] | None = None  # NEW: raw tool calls from LLM
    raw_message: dict | None = None       # NEW: full message for conversation history
```

---

## Orchestrator — Wired Node Functions

### route_next

1. Load workflow config from file
2. Use Router.get_next_stages(completed_stages) to find ready stages
3. If no stages ready → set `status="completed"`
4. If stages ready → set `current_stage` to first ready stage name
5. Return updated state

Sequential only for PoC — picks first ready stage. Parallel execution deferred.

### execute_stage

1. Look up agent config from AgentRegistry using `stage.agent`
2. Resolve model: stage model override → agent default_model
3. Create git worktree via WorktreeManager.create(task_id, stage_name)
4. Build task context string:
   - Always includes: task description
   - If architect plan exists in `stage_outputs["plan"]`: append it
5. Create AgentRunner with LLMProvider and tools
6. Call runner.run() → get AgentResult
7. Store result in `stage_outputs[stage_name]`
8. Accumulate `total_tokens` and `total_cost_usd`
9. Return updated state

### evaluate_gate

1. Get gate config from workflow stage
2. For `automated` gate with `tests_pass` check:
   - Run `pytest` in the worktree via ShellTool
   - Pass if exit code == 0
3. Call `evaluate_gate()` function with check results
4. If passed:
   - Merge worktree changes to task branch (git merge)
   - Add stage to `completed_stages`
   - Clean up worktree
5. If failed:
   - Increment `retry_counts[stage]`
   - If under max_retries → keep `current_stage` (will re-execute)
   - If over max_retries → set `status="error"` with message
   - Clean up worktree
6. For `approval` gate (used by plan stage):
   - Auto-approve for PoC (no human input)
7. Return updated state

---

## Two-Stage PoC Workflow

```yaml
# config/workflows/two-stage.yaml
name: "Two-Stage Proof of Concept"
concurrency: 1
max_cost_usd: 5.0
classifier_mode: disabled
stages:
  - name: plan
    agent: architect
    gate:
      type: approval  # auto-approved in PoC

  - name: backend
    agent: backend-dev
    depends_on: plan
    gate:
      type: automated
      checks:
        - tests_pass
      max_retries: 2
```

---

## Test Repo

A minimal Python project for controlled testing:

```
tests/fixtures/test-repo/
├── src/
│   └── calculator.py       # add(a, b), subtract(a, b)
├── tests/
│   └── test_calculator.py  # Tests for add and subtract
├── pyproject.toml           # pytest configured
└── README.md
```

**calculator.py:**
```python
def add(a: float, b: float) -> float:
    return a + b

def subtract(a: float, b: float) -> float:
    return a - b
```

**Test task:** "Add a multiply(a, b) function to the calculator and write tests for it."

This is ideal because:
- 2-3 tool calls per agent (read → modify → test)
- Deterministic pass/fail via pytest
- Small enough for fast iteration

---

## Task Branch & Merge Mechanics

The **CLI** creates the task branch before invoking the orchestrator:

1. CLI creates branch `fleet/task-{id}` from current HEAD
2. `WorktreeManager.create()` branches each stage off `fleet/task-{id}` (not HEAD)
   - Requires modifying `WorktreeManager.create()` to accept a `base_branch` parameter
   - Stage branch: `fleet/{task_id}/{stage}`, branched from `fleet/task-{id}`
3. After gate passes, `evaluate_gate` does:
   - `git add -A && git commit -m "feat({stage}): agent output"` in the worktree
   - `git checkout fleet/task-{id} && git merge fleet/{task_id}/{stage}` in the main repo
   - Clean up worktree
4. On retry, a fresh worktree is created from `fleet/task-{id}` (includes prior stage merges). Retries start from scratch — the failed attempt is discarded.

### stage_outputs Shape

`stage_outputs` stores `AgentResult.model_dump()` — the full serialized result:

```python
state["stage_outputs"]["plan"] = {
    "success": True,
    "output": "## Plan\n\n### Files to Change\n...",  # The plan text
    "files_changed": [],
    "tokens_used": 1500,
    "iterations": 3,
    "tool_calls": [...]
}
```

The backend stage reads the plan via `state["stage_outputs"]["plan"]["output"]` to get the architect's markdown plan text.

---

## CLI Wiring

`fleet run --repo PATH --task "description" --workflow two-stage` invokes the orchestrator directly (no API server):

1. Load workflow config
2. Load agent registry
3. Create task record in SQLite
4. Create task branch `fleet/task-{id}` from current HEAD
5. Build initial FleetState
6. Run orchestrator graph
7. Print result (success/failure, files changed, tokens used)

---

## End-to-End Flow

```
fleet run --repo ./tests/fixtures/test-repo --task "Add multiply(a, b)" --workflow two-stage
  │
  ├── 1. Create task record (status: queued)
  ├── 2. Create branch fleet/task-{id}
  │
  ├── 3. route_next → current_stage: "plan"
  ├── 4. execute_stage(plan)
  │      └── Architect reads calculator.py, produces markdown plan
  ├── 5. evaluate_gate(plan)
  │      └── Approval gate: auto-approve
  │
  ├── 6. route_next → current_stage: "backend"
  ├── 7. execute_stage(backend)
  │      └── Backend Dev reads plan + code, adds multiply(), writes test
  ├── 8. evaluate_gate(backend)
  │      └── Runs pytest in worktree, pass/fail
  │      └── Pass → merge to task branch
  │
  ├── 9. route_next → no more stages → status: completed
  └── Output: task branch with multiply() + passing tests
```

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| **Create** | `src/agent_fleet/agents/runner.py` | AgentRunner class with ReAct tool loop |
| **Create** | `src/agent_fleet/tools/registry.py` | Map tool names to concrete tool instances |
| **Create** | `config/workflows/two-stage.yaml` | PoC workflow: plan + backend |
| **Create** | `tests/fixtures/test-repo/` | Minimal calculator project |
| **Modify** | `src/agent_fleet/core/orchestrator.py` | Wire real logic into node functions |
| **Modify** | `src/agent_fleet/models/provider.py` | Add tool_calls and raw_message to LLMResponse |
| **Modify** | `cli/main.py` | Wire `fleet run` to invoke orchestrator |

---

## Edge Cases & Error Handling

- **WorktreeManager.create() failure:** `execute_stage` catches `WorktreeError` and sets `status="error"` + `error_message` on state.
- **pytest availability:** The test repo uses the system/venv `pytest`. The gate runs `python -m pytest` (which works if pytest is installed in the active Python) rather than bare `pytest` to avoid PATH issues.
- **Token budget:** Soft limit — checked after each LLM call. A single call can exceed the budget. This is acceptable for PoC.
- **Retry semantics:** Retries start from scratch on a fresh worktree branched from the task branch (which includes prior stage merges). The failed attempt's worktree is cleaned up.
- **LLM tool_choice:** Default `"auto"` is used. No forced tool use for PoC.

---

## What's NOT in Scope

- Parallel stage execution (sequential only)
- PR creation (verify task branch has changes instead)
- API server invocation (CLI direct only)
- Human-in-the-loop approval (auto-approve plan gate)
- Intent classifier
- Event persistence to database (log to structlog only)
- Cost tracking beyond token counting
- Retry with LLM failure context (simple re-run for now)
