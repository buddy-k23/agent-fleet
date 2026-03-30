# Project CRUD + Project Selector — Design Spec

**EPIC:** #185 — Project Detail / Edit / Delete + Project Selector
**Date:** 2026-03-29
**Status:** Approved

---

## Problem

The Projects UI page exists and shows project cards, but the backend has no API routes — the UI inserts directly into Supabase. There's no project detail page, no edit/delete capability, and the SubmitTask form doesn't link tasks to projects. The `tasks` table lacks a `project_id` column.

## Decision Record

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Project deletion | Unlink tasks (`project_id = null`) | Safest — no data loss, tasks survive |
| Detail page | Dedicated `/projects/:id` route | Shows tasks + metadata + submit shortcut |
| Edit UX | Inline on detail page | One fewer navigation step |
| Project selector | Dropdown on SubmitTask form | Pre-fills repo when project selected |
| API pattern | Same as agents/workflows routes | Consistency with existing codebase |

---

## Component Design

### 1. Supabase Migration

**Add `project_id` FK to tasks table:**
```sql
ALTER TABLE tasks ADD COLUMN project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
```

**Add `updated_at` trigger for projects:**
```sql
CREATE TRIGGER update_projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

The `update_updated_at()` function already exists from the initial schema migration.

### 2. `SupabaseProjectRepository`

New class in `src/agent_fleet/store/supabase_repo.py`:

```python
class SupabaseProjectRepository:
    def __init__(self, client: Client) -> None
    def create(self, user_id: str, data: dict) -> dict
    def get(self, project_id: str) -> dict | None
    def list_by_user(self, user_id: str) -> list[dict]
    def update(self, project_id: str, data: dict) -> dict
    def delete(self, project_id: str) -> None
```

Follows the same pattern as `SupabaseAgentRepository` and `SupabaseWorkflowRepository`.

### 3. API Routes — `src/agent_fleet/api/routes/projects.py`

| Method | Path | Behavior |
|--------|------|----------|
| `GET` | `/api/v1/projects` | List user's projects |
| `GET` | `/api/v1/projects/{id}` | Project detail (includes task count) |
| `POST` | `/api/v1/projects` | Create project |
| `PUT` | `/api/v1/projects/{id}` | Update project metadata |
| `DELETE` | `/api/v1/projects/{id}` | Delete project, unlink tasks |

All routes use `get_current_user` from `deps.py`. GET by ID and DELETE verify `user_id` matches.

On DELETE: the Supabase FK `ON DELETE SET NULL` handles task unlinking automatically.

**Pydantic schemas:**

```python
class ProjectCreateRequest(BaseModel):
    name: str
    repo_path: str
    languages: list[str] = []
    frameworks: list[str] = []
    test_frameworks: list[str] = []
    databases: list[str] = []
    has_ci: bool = False
    ci_platform: str | None = None
    has_docker: bool = False
    estimated_loc: int | None = None

class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    repo_path: str | None = None
    languages: list[str] | None = None
    frameworks: list[str] | None = None
    # ... same optional fields

class ProjectResponse(BaseModel):
    id: str
    name: str
    repo_path: str
    languages: list[str]
    frameworks: list[str]
    test_frameworks: list[str]
    databases: list[str]
    has_ci: bool
    ci_platform: str | None
    has_docker: bool
    estimated_loc: int | None
    created_at: datetime
    updated_at: datetime
    task_count: int = 0  # populated on detail endpoint
```

### 4. UI — Project Cards (Edit/Delete Actions)

On the existing Projects listing page (`Projects.tsx`), add to each project card:
- **Edit icon button** → navigates to `/projects/:id` (detail page)
- **Delete icon button** → confirmation dialog → `DELETE /api/v1/projects/:id`

### 5. UI — Project Detail Page

New page: `fleet-ui/src/pages/ProjectDetail/ProjectDetail.tsx`
Route: `/projects/:id`

**Sections:**
- **Header:** Project name, repo path, edit button
- **Metadata:** Languages, frameworks, test frameworks, databases, LOC, CI info — editable inline
- **Task History:** Table of tasks filtered by `project_id`, with status badges, description, created date, link to Task Monitor
- **"New Task" button:** Navigates to `/submit?project_id=X&repo=Y` — pre-fills the SubmitTask form

### 6. UI — SubmitTask Project Selector

Update `SubmitTask.tsx`:
- Add a **Project dropdown** above the repo field
- Fetch user's projects from `GET /api/v1/projects`
- When a project is selected: pre-fill `repo` field with `project.repo_path`, store `project_id`
- Send `project_id` in the API call
- Support URL params: `?project_id=X&repo=Y` for pre-fill from detail page

### 7. Tasks Route Update

Update `SupabaseTaskRepository.create()` to accept and store `project_id`.
Update `GET /api/v1/tasks` to support optional `?project_id=X` filter.

---

## Scope Boundaries

**In scope:**
1. Supabase migration (project_id FK + updated_at trigger)
2. `SupabaseProjectRepository` in store layer
3. `/api/v1/projects` CRUD routes + schemas
4. Project detail page (metadata + task history + submit shortcut)
5. Edit/delete actions on project cards
6. SubmitTask project selector dropdown
7. Task creation stores `project_id`
8. Tests for all new backend code

**Out of scope:**
- Project-level analytics or cost tracking
- Bulk task operations on a project
- Project sharing between users
- Project templates

---

## File Inventory

**New files:**
- `supabase/migrations/20260329000000_add_project_id_to_tasks.sql`
- `src/agent_fleet/api/routes/projects.py`
- `src/agent_fleet/api/schemas/projects.py`
- `fleet-ui/src/pages/ProjectDetail/ProjectDetail.tsx`
- `tests/unit/test_projects_route.py`

**Modified files:**
- `src/agent_fleet/store/supabase_repo.py` — add `SupabaseProjectRepository`
- `src/agent_fleet/main.py` — register projects router
- `src/agent_fleet/api/routes/tasks.py` — support `project_id` filter
- `src/agent_fleet/store/supabase_repo.py` — update `SupabaseTaskRepository.create()` for project_id
- `fleet-ui/src/pages/Projects/Projects.tsx` — add edit/delete actions on cards
- `fleet-ui/src/pages/SubmitTask/SubmitTask.tsx` — add project selector
- `fleet-ui/src/App.tsx` — add ProjectDetail route

---

## Test Strategy

**Unit tests (mocked Supabase):**
- `test_projects_route.py`: CRUD operations, user scoping, delete unlinks tasks
- Update `test_api_tasks.py`: task creation with project_id, filter by project_id

**Manual verification:**
- Create project → appears in listing
- Click card → detail page shows metadata
- Edit metadata → saved
- "New Task" → SubmitTask pre-filled
- Submit task with project → task appears in project detail
- Delete project → tasks survive with null project_id
