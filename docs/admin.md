# Admin Guide

## API Key Management

### Adding Keys (Settings Page)
1. Go to **Settings** → **API Keys**
2. Click **Add Key**
3. Select provider (Anthropic, OpenAI, Google, Ollama)
4. Paste your API key
5. Add a label (optional, e.g., "Production")
6. Click **Save Key**

### Testing Keys
Click **Test** next to any key. It makes a minimal API call to verify:
- Anthropic: sends a 1-token request to Haiku
- OpenAI: lists available models
- Ollama: pings the local server

### How Keys Are Used
When running a pipeline, the system:
1. Checks for a stored key matching the model's provider
2. If found → uses it (decrypted server-side)
3. If not → falls back to env var (ANTHROPIC_API_KEY, etc.)

Keys are encrypted with Fernet and never returned in plain text.

## Admin Dashboard

Go to **Admin** in the sidebar.

### System Stats
- **Users** — total registered users
- **Tasks** — total pipeline tasks
- **Tokens** — total LLM tokens consumed
- **Agents** — total configured agents

### Recent Tasks
Table of the last 20 tasks with ID, description, status, tokens, date.

## User Management

For now, use **Supabase Studio** (http://localhost:54323):
- Authentication → Users → view, disable, delete users
- Table Editor → profiles → edit display names

## Monitoring

### Log Events to Watch
The backend uses `structlog` with JSON output. Key events:

| Event | Meaning |
|-------|---------|
| `task_submitted` | New pipeline task |
| `stage_executed` | Agent completed a stage |
| `gate_passed` / `gate_failed` | Quality gate result |
| `rate_limit_retry` | LLM rate limit hit, retrying |
| `agent_run_failed` | Agent error (check error field) |
| `worktree_created` / `worktree_cleaned` | Git worktree lifecycle |

### Token Usage
Track per task in the Dashboard, or aggregate in Admin.
