# UI Guide

## Pages

### Login / Signup
- Email + password authentication via Supabase Auth
- Protected routes redirect to `/login` if not authenticated

### Dashboard (`/`)
- **KPI Cards** — Active tasks, completed, total tokens, success rate
- **Task Table** — sortable, filterable by status (All/Running/Completed/Error)
- **Realtime** — updates automatically via Supabase Realtime
- Click a task row → navigates to Task Monitor

### Chat (`/chat`)
- **Conversation List** — left sidebar, create new chat
- **Agent Selector** — choose which agent to talk to
- **Message Thread** — user/agent message bubbles with markdown
- **Quick Actions** — Review code, Plan feature, Browse files, Run tests
- **Streaming** — responses stream token-by-token with cursor animation

### Submit Task (`/submit`)
- Repository path input
- Task description (textarea)
- Workflow dropdown (populated from Supabase)
- Optional project selector
- Submit → calls `POST /api/v1/tasks` (API-mediated, not a direct Supabase insert) → redirects to Task Monitor

### Task Monitor (`/tasks/:id`)
- **Pipeline Visualizer** — 6 stage nodes with status colors (gray/indigo/green/red)
- **Progress Bar** — percentage of stages completed
- **Agent Cards** — per-stage metrics (tokens, status, model)
- **Gate Results** — pass/fail with score for review gates

### Agents (`/agents`)
- **Card Grid** — all agents with model chip, tool badges
- **Search** — filter by name/description
- **Create/Edit** — dialog with all fields + live YAML preview
- **Model Dropdown** — grouped by provider (Anthropic/OpenAI/Google/Ollama)
- **Tool Chips** — toggle code, shell, browser, search, api

### Workflows (`/workflows`)
- **React Flow Canvas** — drag-drop pipeline stages
- **Color-coded Nodes** — by agent role
- **Properties Panel** — click node to configure agent, gate type
- **Export YAML** — copy to clipboard
- **Save** — persist to Supabase

### Projects (`/projects`)
- **Project List** — onboarded projects with language/framework chips
- **Onboarding Wizard** — 4-step: repo → detected stack → agents → confirm

### Settings (`/settings`)
- **Profile** — display name, email
- **Model Registry** — provider connection status
