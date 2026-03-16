# Workflow Configuration Guide

## YAML Schema

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| name | string | required | Workflow name |
| concurrency | int | 1 | Max parallel tasks per repo |
| max_cost_usd | float | null | Cost kill switch |
| classifier_mode | string | suggest | suggest/override/disabled |
| stages | list | required | Pipeline stages |

## Stage Schema

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| name | string | required | Stage identifier |
| agent | string | required | Agent name |
| model | string | null | Model override |
| depends_on | str/list | [] | Dependencies |
| max_iterations | int | null | Override agent default |
| gate | object | automated | Gate config |

## Gate Types

| Type | Config | Behavior |
|------|--------|----------|
| automated | `checks: [tests_pass]` | Run pytest, pass/fail |
| score | `min_score: 80` | Parse reviewer JSON, compare |
| approval | — | Auto-approve (for now) |

## Default Pipeline

```
plan → [backend ∥ frontend] → review → e2e → deliver
```

## Parallelism

Stages with the same `depends_on` run concurrently. No explicit `parallel_with` needed.

## Tuning Tips

- `max_iterations`: 10 for architect, 8 for devs, 5 for tester, 3 for reviewer
- Score threshold: 80 for Sonnet/Opus, lower for Haiku
- Tester prompt: "Run tests, report results, DO NOT write documentation"
