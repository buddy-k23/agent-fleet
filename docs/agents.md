# Agent Configuration Guide

## YAML Schema

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| name | string | required | Display name |
| description | string | required | Used for routing |
| default_model | string | required | LiteLLM model ID |
| tools | list[str] | [] | code, shell, browser, search, api |
| capabilities | list[str] | [] | What it can do |
| system_prompt | string | required | Agent instructions |
| max_retries | int | 2 | Gate failure retry limit |
| timeout_minutes | int | 30 | Max execution time |
| max_tokens | int | 100000 | LLM token budget |
| can_delegate | list[str] | [] | Agents it can delegate to |

## Built-in Agents

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| Architect | Sonnet | code, search | Design solutions, create plans |
| Backend Dev | Sonnet | code, shell | Implement server-side code |
| Frontend Dev | Sonnet | code, shell, browser | Build UI components |
| Reviewer | Sonnet | code, search | Review code, score 0-100 |
| Tester | Haiku | code, shell | Run tests, verify correctness |
| Integrator | none | code, shell | Merge branches, create PR |

## Model Selection

| Model | Best for | Cost |
|-------|---------|------|
| Claude Opus 4.6 | Complex architecture | $$$ |
| Claude Sonnet 4.6 | Code generation, review | $$ |
| Claude Haiku 4.5 | Running tests, quick checks | $ |
| GPT-4o | General coding | $$ |
| Ollama/Llama3 | Free, local, private | Free |

**Key lesson:** Don't use Haiku for review — it scores 25/100 on valid code. Use Sonnet minimum.

## Creating a Custom Agent

1. Go to **Agents** page in the UI
2. Click **Create Agent**
3. Fill in name, description, model, tools, system prompt
4. Click **Save** — stored in Supabase
