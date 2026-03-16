# Agent Fleet

Multi-model AI agent orchestration platform. Submit a coding task, and specialized agents (architect, devs, reviewer, tester) collaborate through quality gates to produce a pull request.

Built on **LangGraph + LiteLLM + FastAPI + Supabase + React**.

## Features

- **Multi-model orchestration** — any LLM via LiteLLM (Claude, GPT, Gemini, Ollama)
- **6 built-in agents** — architect, backend dev, frontend dev, reviewer, tester, integrator
- **Quality gates** — automated (pytest), score (reviewer JSON), approval
- **Parallel execution** — stages with same dependencies run concurrently
- **Git worktree isolation** — each agent gets its own workspace
- **Score gate with route-back** — reviewer identifies which stage needs fixes
- **Pluggable PR creation** — GitHub, GitLab, or local summary
- **Agent chatbot** — conversational interface to any agent
- **Project onboarding** — `fleet init` scans codebase, recommends agents + workflow
- **Supabase backend** — auth, database, realtime, storage
- **React dashboard** — KPIs, task table, agent builder, workflow designer, chat
- **Docker setup** — one command: `./setup.sh`

## Quick Start

```bash
# Clone
git clone https://github.com/pkanduri1/agent-fleet.git
cd agent-fleet

# One-command setup (Docker + Supabase local)
./setup.sh

# Or manual setup:
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cd fleet-ui && npm install && cd ..

# Add your LLM API key
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# Start
uvicorn agent_fleet.main:app --reload --port 8000  # Backend
cd fleet-ui && npm run dev                          # Frontend
```

**Access:** http://localhost:3001 (UI) | http://localhost:8000 (API) | http://localhost:54323 (Supabase Studio)

## Architecture

```
CLI / React UI → FastAPI API → LangGraph Orchestrator → Agent Pool → Git Worktrees
                                      ↕
                              Supabase (Auth, DB, Realtime, Storage)
```

## Pipeline

```
plan → [backend ∥ frontend] → review → e2e → deliver → PR
```

## Stats

- 292 Python tests + 45 Playwright E2E tests
- 129 GitHub issues (all closed)
- 6 built-in agents, custom agents via YAML or UI
- Works with Claude, GPT, Gemini, Ollama

## Documentation

- [Setup Guide](docs/setup.md)
- [CLI Reference](docs/cli.md)
- [UI Guide](docs/ui.md)
- [API Reference](docs/api.md)
- [Architecture](docs/architecture.md)
- [Agent Config](docs/agents.md)
- [Workflow Config](docs/workflows.md)
- [Contributing](docs/contributing.md)

## License

MIT
