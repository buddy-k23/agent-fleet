# Workflow Configuration Guide

## YAML Schema

```yaml
name: "Pipeline Name"
concurrency: 1              # Max parallel tasks per repo
max_cost_usd: 50.0          # Cost kill switch (optional)
classifier_mode: suggest     # suggest | override | disabled
stages:
  - name: plan
    agent: architect
    model: anthropic/claude-sonnet-4-6  # Override agent default
    max_iterations: 10
    gate:
      type: approval

  - name: backend
    agent: backend-dev
    depends_on: plan         # Runs after plan completes
    max_iterations: 8
    gate:
      type: automated
      checks: [tests_pass]

  - name: review
    agent: reviewer
    depends_on: [backend, frontend]  # Runs after both
    max_iterations: 3
    gate:
      type: score
      min_score: 80
      on_fail: route_to
      max_retries: 2
```

## Gate Types

| Type | Config | Pass condition |
|------|--------|---------------|
| automated | `checks: [tests_pass]` | pytest exit code 0 |
| score | `min_score: 80` | Reviewer JSON score ≥ 80 |
| approval | — | Auto-approve (human review planned) |
| custom | — | User-defined script |

## Example: Backend-Only Pipeline

```yaml
name: "Backend Pipeline"
stages:
  - name: plan
    agent: architect
    max_iterations: 10
    gate: {type: approval}
  - name: backend
    agent: backend-dev
    depends_on: plan
    max_iterations: 8
    gate: {type: automated, checks: [tests_pass]}
  - name: review
    agent: reviewer
    depends_on: backend
    max_iterations: 3
    gate: {type: score, min_score: 80, max_retries: 2}
  - name: deliver
    agent: integrator
    depends_on: review
    gate: {type: approval}
```

## Example: Hotfix Pipeline

```yaml
name: "Hotfix"
stages:
  - name: fix
    agent: backend-dev
    max_iterations: 5
    gate: {type: automated, checks: [tests_pass]}
  - name: review
    agent: reviewer
    depends_on: fix
    max_iterations: 3
    gate: {type: score, min_score: 70}
  - name: deliver
    agent: integrator
    depends_on: review
    gate: {type: approval}
```

## Parallelism

Stages with the same `depends_on` run concurrently automatically:
```yaml
- name: backend
  depends_on: plan    # ← same dependency
- name: frontend
  depends_on: plan    # ← runs in parallel with backend
```

## Tuning Tips

| Stage | max_iterations | Why |
|-------|---------------|-----|
| Architect | 10 | Needs to read multiple files |
| Dev agents | 8 | Read + write + test |
| Tester | 5 | Just run tests, don't write docs |
| Reviewer | 3 | Read + score, minimal tool use |

**Score gate threshold:** 80 for Sonnet/Opus, 40 for Haiku (scores harshly).
