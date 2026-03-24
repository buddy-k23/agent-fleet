# Setup Guide

## Prerequisites

- Python 3.12+ (`brew install python@3.12`)
- Node 18+ (`brew install node`)
- Docker Desktop
- Supabase CLI (`brew install supabase/tap/supabase`)

## Docker Setup (Recommended)

```bash
git clone https://github.com/pkanduri1/agent-fleet.git
cd agent-fleet
./setup.sh
```

This starts everything: Supabase (local Docker), FastAPI backend, React frontend.

**URLs:**
- Frontend: http://localhost:3001
- Backend: http://localhost:8000
- Supabase Studio: http://localhost:54323

**Default login:** `admin@agentfleet.local` / `agentfleet123`

## Manual Setup

### 1. Backend
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Frontend
```bash
cd fleet-ui
npm install
npx playwright install chromium
```

### 3. Supabase
```bash
supabase start          # Start local Supabase
supabase db push --local  # Run migrations
```

### 4. Environment Variables

**.env (backend):**
```bash
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=<from supabase status>
SUPABASE_SERVICE_ROLE_KEY=<from supabase status>
ANTHROPIC_API_KEY=sk-ant-...  # or OPENAI_API_KEY
```

**fleet-ui/.env (frontend):**
```bash
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_ANON_KEY=<from supabase status>
VITE_API_BASE=http://localhost:8000
```

### 5. Seed Data
```bash
# Find user_id from Supabase Studio > Authentication > Users
python scripts/seed_supabase.py <user_id>
```

### 6. Start
```bash
# Terminal 1
uvicorn agent_fleet.main:app --reload --port 8000

# Terminal 2
cd fleet-ui && npm run dev

# Terminal 3
python -m agent_fleet.worker
```

### 7. Verify
- http://localhost:8000/health → `{"status":"ok"}`
- http://localhost:3001 → Login page

## LLM API Keys

| Provider | Env var | Get key |
|----------|---------|---------|
| Anthropic | ANTHROPIC_API_KEY | console.anthropic.com |
| OpenAI | OPENAI_API_KEY | platform.openai.com |
| Google | GOOGLE_API_KEY | ai.google.dev |
| Ollama | OLLAMA_API_BASE=http://localhost:11434 | Local (free) |

## Troubleshooting

- **"Credit balance too low"** → API key workspace doesn't match billing
- **Blank UI** → Check `.env` has `VITE_` prefix, rebuild frontend
- **"Database error saving new user"** → Run trigger fix migration
- **Reviewer scores too low** → Use Sonnet (not Haiku) for reviewer
