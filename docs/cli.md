# CLI Reference

## Commands

### `fleet version`
Show version.
```bash
$ fleet version
Agent Fleet v0.1.0
```

### `fleet run`
Run a pipeline against a repository.
```bash
fleet run --repo /path/to/repo --task "Add multiply function" --workflow default
```

| Option | Default | Description |
|--------|---------|-------------|
| `--repo` | required | Path to git repository |
| `--task` | required | Task description |
| `--workflow` | default | Workflow name (default, two-stage) |

### `fleet init`
Onboard a project — scan codebase and recommend agents + workflow.
```bash
fleet init --repo /path/to/project
```

| Option | Default | Description |
|--------|---------|-------------|
| `--repo` | required | Path to project |
| `--dry-run` | true | Display only, don't save |

### `fleet agents list`
List configured agents.
```bash
$ fleet agents list
  architect            Analyzes codebase, designs solutions
  backend-dev          Implements API endpoints, services
  frontend-dev         Implements React UI components
  reviewer             Reviews code for bugs, security
  tester               Writes and runs tests
  integrator           Merges worktrees, creates PR
```

### `fleet status`
Check task status (stub — use UI or API instead).
```bash
fleet status <task-id>
```
