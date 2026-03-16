#!/bin/bash
set -e

GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
BOLD="\033[1m"
NC="\033[0m"

log() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
err() { echo -e "${RED}✗${NC} $1"; exit 1; }
header() { echo -e "\n${BOLD}${CYAN}$1${NC}\n"; }

header "Agent Fleet — Setup"

# ── Step 1: Prerequisites ──
header "Step 1: Prerequisites"
command -v docker >/dev/null 2>&1 || err "Docker not found. Install from https://docker.com"
command -v supabase >/dev/null 2>&1 || err "Supabase CLI not found. Run: brew install supabase/tap/supabase"
log "Docker: $(docker --version | head -c 40)"
log "Supabase CLI: $(supabase --version 2>/dev/null | head -1)"

# ── Step 2: Start Supabase ──
header "Step 2: Starting Supabase (local Docker)"
supabase start 2>&1 | tail -20
log "Supabase started"

# Get the keys from supabase status
SUPABASE_URL=$(supabase status --output json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['API_URL'])" 2>/dev/null || echo "http://localhost:54321")
ANON_KEY=$(supabase status --output json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['ANON_KEY'])" 2>/dev/null || echo "")
SERVICE_ROLE_KEY=$(supabase status --output json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['SERVICE_ROLE_KEY'])" 2>/dev/null || echo "")

log "Supabase URL: $SUPABASE_URL"

# ── Step 3: Run migrations ──
header "Step 3: Running migrations"
supabase db push --local 2>&1 || warn "Migrations may have already been applied"
log "Migrations applied"

# ── Step 4: Create .env files ──
header "Step 4: Creating env files"
cat > .env << ENVEOF
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_ANON_KEY=${ANON_KEY}
SUPABASE_SERVICE_ROLE_KEY=${SERVICE_ROLE_KEY}
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
ENVEOF

cat > fleet-ui/.env << FEEOF
VITE_SUPABASE_URL=${SUPABASE_URL}
VITE_SUPABASE_ANON_KEY=${ANON_KEY}
VITE_API_BASE=http://localhost:8000
FEEOF
log "Env files created"

# ── Step 5: Build + start backend/frontend ──
header "Step 5: Building backend + frontend"
docker compose build --quiet 2>&1
docker compose up -d 2>&1
log "Backend + frontend started"

# ── Step 6: Create user + seed ──
header "Step 6: Creating default user + seeding data"

# Create user via Supabase local auth
SIGNUP=$(curl -s -X POST "${SUPABASE_URL}/auth/v1/signup" \
    -H "Content-Type: application/json" \
    -H "apikey: ${ANON_KEY}" \
    -d '{"email":"admin@agentfleet.local","password":"agentfleet123"}')

USER_ID=$(echo "$SIGNUP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -n "$USER_ID" ] && [ "$USER_ID" != "" ]; then
    log "User created: admin@agentfleet.local (ID: ${USER_ID})"

    # Seed
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        export SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY
        python3 scripts/seed_supabase.py "$USER_ID" 2>&1 || warn "Seed failed — run manually later"
    else
        warn "Python venv not found — run seed manually: python scripts/seed_supabase.py $USER_ID"
    fi
else
    warn "User creation failed or already exists"
fi

# ── Done ──
header "Setup Complete!"
echo -e "${BOLD}URLs:${NC}"
echo -e "  ${CYAN}Frontend:${NC}        http://localhost:3001"
echo -e "  ${CYAN}Backend API:${NC}     http://localhost:8000"
echo -e "  ${CYAN}Supabase Studio:${NC} http://localhost:54323"
echo -e "  ${CYAN}Supabase API:${NC}    ${SUPABASE_URL}"
echo ""
echo -e "${BOLD}Login:${NC}"
echo -e "  Email:    ${GREEN}admin@agentfleet.local${NC}"
echo -e "  Password: ${GREEN}agentfleet123${NC}"
echo ""
echo -e "${BOLD}Next:${NC}"
echo -e "  1. Add your LLM API key to .env"
echo -e "  2. Restart backend: docker compose restart backend"
echo -e "  3. Open http://localhost:3001"
echo ""
echo -e "${BOLD}Commands:${NC}"
echo -e "  supabase status        — Supabase info + keys"
echo -e "  docker compose ps      — backend/frontend status"
echo -e "  supabase stop          — stop Supabase"
echo -e "  docker compose down    — stop backend/frontend"
