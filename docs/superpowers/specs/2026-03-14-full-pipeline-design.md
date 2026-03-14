# Full 6-Stage Pipeline — Design Specification

## Overview

Extend the working two-stage pipeline (plan + backend) to the full 6-stage default pipeline: plan → backend → frontend → review → e2e → deliver. This completes the core product loop: task in → PR out.

**Prior specs:**
- `docs/superpowers/specs/2026-03-13-agent-fleet-design.md` (v1 architecture)
- `docs/superpowers/specs/2026-03-14-agent-runner-e2e-design.md` (v2 agent runner)

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Parallel execution | Sequential for now | Get all 6 stages working first, add parallelism later |
| Review route-back | Reviewer specifies target stage in JSON | More precise than always routing to backend |
| PR creation | Pluggable provider (GitHub, GitLab, local fallback) | Provider-agnostic, works offline |
| Test repo | Keep calculator, frontend is a no-op | Validates pipeline flow without new fixtures |

---

## What Changes

3 of the 4 new stages need zero code changes — the existing orchestrator handles arbitrary stages via workflow YAML + agent registry. The real work:

| Change | File | What |
|--------|------|------|
| **Create** | `src/agent_fleet/workspace/pr.py` | PRProvider ABC + GitHub, GitLab, Local implementations |
| **Modify** | `src/agent_fleet/core/orchestrator.py` | Score gate parsing, route_to from reviewer JSON, integrator shortcut |
| **Modify** | `config/workflows/default.yaml` | Add Haiku model overrides for cost control |

---

## Score Gate (Review Stage)

The reviewer agent produces structured JSON output:

```json
{
  "score": 75,
  "reasoning": "Missing edge case tests for negative numbers",
  "issues": [
    {"file": "src/calculator.py", "line": 15, "severity": "medium", "description": "No input validation"}
  ],
  "route_to": "backend"
}
```

### evaluate_gate changes for score gate:

1. Get the reviewer's output from `stage_outputs["review"]["output"]`
2. Parse as JSON (try/except — if parsing fails, treat as score=0)
3. Extract `score` field, compare against gate's `min_score`
4. **If passed** (score >= min_score): add review to completed_stages
5. **If failed** (score < min_score):
   - Read `route_to` from the JSON (e.g., "backend" or "frontend")
   - If `route_to` not in JSON, fall back to gate config's `route_target`
   - Remove the target stage from `completed_stages` so it re-executes
   - Inject reviewer feedback into the retried agent's task context via `stage_outputs["review"]`
   - Increment retry_counts

### Task context for retried stage:

When a stage is re-run after review failure, the task context includes:
```
Task: {original description}

## Architect's Plan
{plan output}

## Reviewer Feedback (score: 75/100)
{reviewer reasoning + issues}

Please address the reviewer's feedback.
```

---

## PR Creation (Deliver Stage)

The deliver stage is a specialized stage — it doesn't call an LLM. It performs git operations and creates a PR.

### Pluggable PR Provider

```python
# workspace/pr.py
class PRProvider(ABC):
    @abstractmethod
    def create_pr(self, repo_path, branch, title, body) -> str | None:
        """Create a PR/MR. Returns URL on success, None on failure."""

class GitHubPRProvider(PRProvider):
    """Uses `gh pr create` CLI."""

class GitLabPRProvider(PRProvider):
    """Uses `glab mr create` CLI."""

class LocalSummaryProvider(PRProvider):
    """Writes summary to fleet-summary.md in repo root. Always succeeds."""
```

### Provider Detection

1. Check if `gh` CLI exists and repo has GitHub remote → `GitHubPRProvider`
2. Check if `glab` CLI exists and repo has GitLab remote → `GitLabPRProvider`
3. Otherwise → `LocalSummaryProvider`

### PR Body / Summary Content

Generated from stage outputs:
```markdown
## Agent Fleet Task Summary

**Task:** {description}
**Workflow:** {workflow_name}
**Total tokens:** {total_tokens}

### Stages

#### Plan (Architect)
{plan output summary}

#### Backend (Backend Dev)
Files changed: {files list}
{output summary}

#### Frontend (Frontend Dev)
{output or "No changes needed"}

#### Review (Reviewer)
Score: {score}/100
{reasoning}

#### E2E (Tester)
{test results summary}
```

### execute_stage shortcut for integrator

When `stage.agent == "integrator"`, `execute_stage` skips the AgentRunner and instead:
1. Generate summary from all stage_outputs
2. Detect PR provider
3. Call `provider.create_pr()`
4. Store result in stage_outputs and pr_url

---

## Workflow Config Update

`config/workflows/default.yaml` updated with Haiku model overrides for cost control:

```yaml
stages:
  - name: plan
    agent: architect
    model: anthropic/claude-haiku-4-5-20251001
    gate:
      type: approval

  - name: backend
    agent: backend-dev
    model: anthropic/claude-haiku-4-5-20251001
    depends_on: plan
    gate:
      type: automated
      checks: [tests_pass]

  - name: frontend
    agent: frontend-dev
    model: anthropic/claude-haiku-4-5-20251001
    depends_on: plan
    gate:
      type: automated
      checks: [tests_pass]

  - name: review
    agent: reviewer
    model: anthropic/claude-haiku-4-5-20251001
    depends_on: [backend, frontend]
    gate:
      type: score
      min_score: 80
      on_fail: route_to
      max_retries: 2

  - name: e2e
    agent: tester
    model: anthropic/claude-haiku-4-5-20251001
    depends_on: review
    gate:
      type: automated
      checks: [all_tests_pass]

  - name: deliver
    agent: integrator
    depends_on: e2e
    actions: [create_pr]
```

Note: `route_target` removed from review gate config — it's now read from the reviewer's JSON output, with fallback to the first stage in `depends_on`.

---

## End-to-End Flow

```
fleet run --repo ./test-repo --task "Add multiply" --workflow default

route_next → plan
  Architect reads code, produces plan
  Gate: approval (auto-approve)

route_next → backend
  Backend Dev adds multiply() + tests (uses plan as context)
  Gate: automated (pytest passes)

route_next → frontend
  Frontend Dev: "no frontend changes needed"
  Gate: automated (pytest passes — no changes = still passes)

route_next → review
  Reviewer reads all changes, produces score + feedback
  Gate: score >= 80
    Pass → continue
    Fail → read route_to from JSON, re-run that stage with feedback

route_next → e2e
  Tester runs full test suite
  Gate: automated (all tests pass)

route_next → deliver
  Integrator: generate summary, create PR (or local summary)
  Gate: approval (auto-approve)

route_next → no more stages → status: completed
```

---

## What's NOT in Scope

- Parallel stage execution (sequential only, parallelism is a follow-up)
- Human-in-the-loop approval (all approval gates auto-approve)
- Cost tracking beyond token counting
- New test repo (calculator with no-op frontend is sufficient)
