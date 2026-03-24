# Contributing Guide

## Dev Setup

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cd fleet-ui && npm install && npx playwright install chromium
```

## Running Tests

> **Integration tests** require the worker process to be running alongside the API server.
> Start it before running `pytest tests/integration/`:
> ```bash
> python -m agent_fleet.worker &
> ```

| Suite | Command | Count |
|-------|---------|-------|
| Python unit | `pytest tests/unit/` | ~304 |
| Python integration | `pytest tests/integration/` | ~40 |
| Playwright E2E | `cd fleet-ui && npx playwright test` | ~45 |
| Lint | `ruff check src/ cli/ tests/` | 0 errors |

## Code Conventions

### 7 Architecture Principles (from CLAUDE.md)
1. Orchestrator owns the flow
2. Agents are config, not code
3. LiteLLM for all model calls
4. Tools are sandboxed
5. Worktree isolation
6. Event-sourced state
7. Fail-safe by default

### Implementation Rules
- Type hints everywhere
- Tests first (TDD)
- No global state — use DI
- Structured logging (structlog)
- Pydantic for schemas

### Commit Convention
```
feat(scope): description (#issue)
fix(scope): description (#issue)
test(scope): description (#issue)
```

Scopes: core, agents, api, cli, tools, workspace, store, ui

### Design System
- Style: Flat Design
- Colors: Indigo (#6366F1) + Emerald (#10B981)
- Fonts: Fira Code (headings) + Fira Sans (body)
- `data-testid` on all interactive UI elements

## PR Process
1. Create branch from main
2. Implement with TDD
3. Run `pytest` + `ruff check` + `npx playwright test`
4. Commit with conventional format
5. Push + create PR
6. Review + merge
