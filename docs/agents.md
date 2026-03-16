# Agent Configuration Guide

## YAML Schema

```yaml
name: "Agent Name"                    # Display name (required)
description: "What this agent does"   # Used for routing (required)
default_model: "anthropic/claude-sonnet-4-6"  # LiteLLM model ID
tools:                                # Tool categories
  - code                              # read/write/list files
  - shell                             # run commands
  - browser                           # Playwright (planned)
  - search                            # web search (planned)
capabilities:                         # What it can do
  - code_analysis
  - testing
system_prompt: |                      # Agent instructions
  You are a backend developer...
max_retries: 2                        # Gate failure retries
timeout_minutes: 30                   # Max execution time
max_tokens: 100000                    # LLM token budget
can_delegate:                         # Agents it can delegate to
  - backend-dev
```

## Built-in Agents

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| Architect | Sonnet | code, search | Analyzes codebase, creates implementation plans |
| Backend Dev | Sonnet | code, shell | Implements server-side code, runs tests |
| Frontend Dev | Sonnet | code, shell, browser | Builds UI components |
| Reviewer | Sonnet | code, search | Reviews code, outputs JSON score 0-100 |
| Tester | Haiku | code, shell | Runs test suite, reports results |
| Integrator | none | code, shell | Merges branches, creates PR (no LLM) |

## Model Selection Guide

| Use Case | Recommended | Why |
|----------|------------|-----|
| Architecture decisions | Opus or Sonnet | Complex reasoning |
| Code generation | Sonnet | Good balance of quality + speed |
| Code review | Sonnet (NOT Haiku) | Haiku scores 25/100 on valid code |
| Running tests | Haiku | Just executes commands, cheap |
| Quick checks | GPT-4o-mini or Haiku | Fast, low cost |
| Privacy-sensitive | Ollama/Llama3 | Runs locally, no data leaves |

## Tutorial: Create a Custom DBA Agent

### Via UI (Agent Builder)
1. Go to **Agents** page → **Create Agent**
2. Name: `DBA`
3. Description: `Database migration specialist`
4. Model: Claude Sonnet 4.6
5. Tools: toggle `code` + `shell`
6. System prompt:
```
You are a database migration specialist. You:
1. Read existing schema and migration files
2. Write new migrations (Liquibase, Alembic, or Prisma)
3. Always include rollback scripts
4. Test migrations by running them
Never modify existing migration files — create new ones only.
```
7. Click **Save**

### Via YAML
Create `config/agents/dba.yaml`:
```yaml
name: "DBA"
description: "Database migration specialist"
capabilities: [schema_design, migration_writing]
tools: [code, shell]
default_model: "anthropic/claude-sonnet-4-6"
system_prompt: |
  You are a database migration specialist...
max_retries: 1
timeout_minutes: 20
```

## Prompt Engineering Tips

1. **Be specific about output format** — "Output ONLY valid JSON" for reviewers
2. **Name the framework** — "You work with Spring Boot + JdbcTemplate"
3. **Include constraints** — "DO NOT write documentation files"
4. **Add scoring rubric** — "Working code with passing tests = 80+"
5. **Set boundaries** — "Only modify files in src/ directory"
