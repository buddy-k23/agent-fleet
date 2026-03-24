# Docker & Deployment Guide

## Quick Start (Docker)

```bash
./setup.sh
```

This runs 7 steps:
1. Checks prerequisites (Docker, Supabase CLI)
2. Starts local Supabase (`supabase start`)
3. Runs database migrations
4. Creates `.env` files with Supabase keys
5. Builds backend + frontend containers
6. Creates default user
7. Seeds default agents + workflows

## Services

| Service | Port | How it runs |
|---------|------|-------------|
| Supabase (all) | 54321-54323 | `supabase start` (CLI managed) |
| Backend | 8000 | Docker container |
| Frontend | 3001 | Docker container (nginx) |
| Worker | — | Docker container (no exposed port) |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Database error saving new user" | Run trigger fix: `docker exec -i $(docker ps -q -f name=supabase_db) psql -U postgres < supabase/migrations/20260313000001_fix_triggers.sql` |
| Blank UI page | Rebuild frontend: `docker compose build frontend && docker compose up -d frontend` |
| "supabaseUrl is required" | Check `fleet-ui/.env` has `VITE_SUPABASE_URL` set |
| Backend restarting | Check `docker compose logs backend` — likely missing dependency |
| Port conflict | Change ports in `docker-compose.yml` |

## Commands

```bash
docker compose ps          # Check status
docker compose logs -f     # Stream logs
docker compose restart     # Restart all
docker compose down        # Stop all
docker compose build       # Rebuild
supabase status            # Supabase info + keys
supabase stop              # Stop Supabase
```

## Production Deployment

### Option 1: Cloud Supabase + Railway

1. Create project at supabase.com
2. Run migrations: `supabase link && supabase db push`
3. Deploy backend to Railway/Render/Fly.io
4. Deploy frontend to Vercel/Netlify
5. Set env vars on each service

### Option 2: Self-hosted (VPS)

1. Install Docker on VPS
2. Clone repo, run `./setup.sh`
3. Configure reverse proxy (nginx/Caddy) for HTTPS
4. Set real secrets in `.env` (not defaults)

## Environment Variables

| Variable | Where | Description |
|----------|-------|-------------|
| SUPABASE_URL | Backend | Supabase API URL |
| SUPABASE_ANON_KEY | Backend + Frontend | Public key |
| SUPABASE_SERVICE_ROLE_KEY | Backend only | Admin key (secret) |
| ANTHROPIC_API_KEY | Backend | LLM provider |
| OPENAI_API_KEY | Backend | LLM provider |
| VITE_SUPABASE_URL | Frontend | Build-time Supabase URL |
| VITE_SUPABASE_ANON_KEY | Frontend | Build-time public key |
| VITE_API_BASE | Frontend | Backend API URL |
| MAX_CONCURRENT_TASKS | Worker | Max parallel task executions (default: 4) |
| POLL_INTERVAL_SECONDS | Worker | How often worker polls for new tasks (default: 5) |

## Worker

The worker process picks up queued tasks and runs agent pipelines. It mounts `worker-worktrees:/tmp/fleet-worktrees` for git worktree isolation.

**Healthcheck:** `python -m agent_fleet.worker --health`
