# Project CRUD + Project Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build full project CRUD API, project detail page with task history, and project selector on the SubmitTask form — linking tasks to projects end-to-end.

**Architecture:** Add `SupabaseProjectRepository` following the existing repo pattern, create `/api/v1/projects` CRUD routes matching the agents/workflows pattern, add a Supabase migration for `project_id` FK on tasks, build a ProjectDetail page with task history + submit shortcut, and wire the SubmitTask form to send `project_id`.

**Tech Stack:** Python/FastAPI, supabase-py, React/MUI, TypeScript

**Spec:** `docs/superpowers/specs/2026-03-29-project-crud-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| **New** | |
| `supabase/migrations/20260330000000_add_project_id_to_tasks.sql` | Add project_id FK + updated_at trigger |
| `src/agent_fleet/api/routes/projects.py` | CRUD routes for projects |
| `src/agent_fleet/api/schemas/projects.py` | Pydantic request/response models |
| `fleet-ui/src/pages/ProjectDetail/ProjectDetail.tsx` | Detail page with metadata, task history, submit shortcut |
| `tests/unit/test_projects_route.py` | API route tests |
| `tests/unit/test_project_repo.py` | Repository unit tests |
| **Modified** | |
| `src/agent_fleet/store/supabase_repo.py` | Add `SupabaseProjectRepository` |
| `src/agent_fleet/main.py:7-16,35-43` | Register projects router |
| `src/agent_fleet/api/routes/tasks.py:21-39,42-49` | Accept project_id on create, filter by project_id on list |
| `src/agent_fleet/api/schemas/tasks.py` | Ensure project_id flows through TaskResponse |
| `fleet-ui/src/pages/Projects/Projects.tsx` | Add edit/delete actions on cards |
| `fleet-ui/src/pages/SubmitTask/SubmitTask.tsx` | Add project selector dropdown |
| `fleet-ui/src/App.tsx` | Add ProjectDetail route |

---

## Task 1: Supabase Migration

**Files:**
- Create: `supabase/migrations/20260330000000_add_project_id_to_tasks.sql`

- [ ] **Step 1: Create migration file**

```sql
-- Add project_id FK to tasks table
ALTER TABLE tasks ADD COLUMN project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
CREATE INDEX idx_tasks_project_id ON tasks(project_id);

-- Add updated_at trigger for projects (function already exists from initial schema)
CREATE TRIGGER update_projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/20260330000000_add_project_id_to_tasks.sql
git commit -m "feat(store): add project_id FK to tasks + projects updated_at trigger (#185)"
```

---

## Task 2: `SupabaseProjectRepository`

**Files:**
- Modify: `src/agent_fleet/store/supabase_repo.py` (add class after `SupabaseWorkflowRepository`)
- Create: `tests/unit/test_project_repo.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_project_repo.py
"""Tests for SupabaseProjectRepository."""

from unittest.mock import MagicMock

from agent_fleet.store.supabase_repo import SupabaseProjectRepository


class TestProjectRepoCreate:
    def test_create_inserts_with_user_id(self):
        """Create project inserts user_id and data."""
        client = MagicMock()
        row = {"id": "proj-1", "name": "My Project", "user_id": "user-1"}
        client.table.return_value.insert.return_value.execute.return_value.data = [row]

        repo = SupabaseProjectRepository(client)
        result = repo.create("user-1", {"name": "My Project", "repo_path": "/tmp/repo"})

        insert_payload = client.table.return_value.insert.call_args[0][0]
        assert insert_payload["user_id"] == "user-1"
        assert insert_payload["name"] == "My Project"
        assert result == row


class TestProjectRepoGet:
    def test_get_returns_project(self):
        """Get returns project dict."""
        client = MagicMock()
        row = {"id": "proj-1", "name": "My Project"}
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [row]

        repo = SupabaseProjectRepository(client)
        result = repo.get("proj-1")
        assert result == row

    def test_get_returns_none_when_missing(self):
        """Get returns None when project not found."""
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        repo = SupabaseProjectRepository(client)
        assert repo.get("nonexistent") is None


class TestProjectRepoListByUser:
    def test_list_returns_user_projects(self):
        """List returns projects ordered by created_at desc."""
        client = MagicMock()
        rows = [{"id": "p1"}, {"id": "p2"}]
        chain = client.table.return_value.select.return_value
        chain.eq.return_value.order.return_value.execute.return_value.data = rows

        repo = SupabaseProjectRepository(client)
        result = repo.list_by_user("user-1")
        assert result == rows


class TestProjectRepoUpdate:
    def test_update_sends_data(self):
        """Update sends data dict to Supabase."""
        client = MagicMock()
        row = {"id": "proj-1", "name": "Updated"}
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [row]

        repo = SupabaseProjectRepository(client)
        result = repo.update("proj-1", {"name": "Updated"})
        assert result == row


class TestProjectRepoDelete:
    def test_delete_removes_project(self):
        """Delete calls Supabase delete."""
        client = MagicMock()
        client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []

        repo = SupabaseProjectRepository(client)
        repo.delete("proj-1")
        client.table.assert_called_with("projects")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_project_repo.py -v`
Expected: FAIL — `ImportError: cannot import name 'SupabaseProjectRepository'`

- [ ] **Step 3: Implement SupabaseProjectRepository**

Add to `src/agent_fleet/store/supabase_repo.py` after the `SupabaseWorkflowRepository` class:

```python
class SupabaseProjectRepository:
    """Project CRUD via Supabase."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def create(self, user_id: str, data: dict) -> dict:
        """Create a project for a user."""
        data["user_id"] = user_id
        result = self._client.table("projects").insert(data).execute()
        return result.data[0]

    def get(self, project_id: str) -> dict | None:
        """Get project by ID."""
        result = (
            self._client.table("projects")
            .select("*")
            .eq("id", project_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def list_by_user(self, user_id: str) -> list[dict]:
        """List all projects for a user, newest first."""
        result = (
            self._client.table("projects")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data

    def update(self, project_id: str, data: dict) -> dict:
        """Update project metadata."""
        result = (
            self._client.table("projects")
            .update(data)
            .eq("id", project_id)
            .execute()
        )
        return result.data[0]

    def delete(self, project_id: str) -> None:
        """Delete project. Tasks are unlinked via ON DELETE SET NULL."""
        self._client.table("projects").delete().eq("id", project_id).execute()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_project_repo.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_fleet/store/supabase_repo.py tests/unit/test_project_repo.py
git commit -m "feat(store): add SupabaseProjectRepository (#185)"
```

---

## Task 3: Pydantic Schemas + API Routes

**Files:**
- Create: `src/agent_fleet/api/schemas/projects.py`
- Create: `src/agent_fleet/api/routes/projects.py`
- Modify: `src/agent_fleet/main.py`
- Create: `tests/unit/test_projects_route.py`

- [ ] **Step 1: Create Pydantic schemas**

```python
# src/agent_fleet/api/schemas/projects.py
"""Pydantic schemas for project API endpoints."""

from datetime import datetime

from pydantic import BaseModel


class ProjectCreateRequest(BaseModel):
    """Request body for POST /api/v1/projects."""

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
    """Request body for PUT /api/v1/projects/{id}."""

    name: str | None = None
    repo_path: str | None = None
    languages: list[str] | None = None
    frameworks: list[str] | None = None
    test_frameworks: list[str] | None = None
    databases: list[str] | None = None
    has_ci: bool | None = None
    ci_platform: str | None = None
    has_docker: bool | None = None
    estimated_loc: int | None = None


class ProjectResponse(BaseModel):
    """Response body for project endpoints."""

    id: str
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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    """Response body for GET /api/v1/projects/{id} — includes task count."""

    task_count: int = 0
```

- [ ] **Step 2: Create API routes**

```python
# src/agent_fleet/api/routes/projects.py
"""Project CRUD routes backed by Supabase."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException

from agent_fleet.api.deps import get_current_user, get_supabase_client
from agent_fleet.api.schemas.projects import (
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from agent_fleet.store.supabase_repo import SupabaseProjectRepository, SupabaseTaskRepository

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _get_repo() -> SupabaseProjectRepository:
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase not configured")
    return SupabaseProjectRepository(client)


def _get_task_repo() -> SupabaseTaskRepository:
    client = get_supabase_client()
    return SupabaseTaskRepository(client)


@router.get("")
async def list_projects(
    user: dict = Depends(get_current_user),
    repo: SupabaseProjectRepository = Depends(_get_repo),
) -> list[ProjectResponse]:
    """List all projects for the current user."""
    projects = repo.list_by_user(user["id"])
    return [ProjectResponse(**p) for p in projects]


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    repo: SupabaseProjectRepository = Depends(_get_repo),
    task_repo: SupabaseTaskRepository = Depends(_get_task_repo),
) -> ProjectDetailResponse:
    """Get project detail with task count."""
    project = repo.get(project_id)
    if not project or project.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    task_count = task_repo.count_by_project(project_id)
    return ProjectDetailResponse(**project, task_count=task_count)


@router.post("", status_code=201)
async def create_project(
    request: ProjectCreateRequest,
    user: dict = Depends(get_current_user),
    repo: SupabaseProjectRepository = Depends(_get_repo),
) -> ProjectResponse:
    """Create a new project."""
    project = repo.create(user["id"], request.model_dump())
    logger.info("project_created", project_id=project["id"], user_id=user["id"])
    return ProjectResponse(**project)


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    request: ProjectUpdateRequest,
    user: dict = Depends(get_current_user),
    repo: SupabaseProjectRepository = Depends(_get_repo),
) -> ProjectResponse:
    """Update project metadata."""
    project = repo.get(project_id)
    if not project or project.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = request.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = repo.update(project_id, update_data)
    logger.info("project_updated", project_id=project_id)
    return ProjectResponse(**updated)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    repo: SupabaseProjectRepository = Depends(_get_repo),
) -> None:
    """Delete project. Tasks are unlinked (project_id set to null)."""
    project = repo.get(project_id)
    if not project or project.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    repo.delete(project_id)
    logger.info("project_deleted", project_id=project_id, user_id=user["id"])
```

- [ ] **Step 3: Register router in main.py**

Add to the imports (line 7-16):
```python
from agent_fleet.api.routes import (
    agents,
    api_keys,
    approvals,
    audit,
    chat,
    profile,
    projects,
    tasks,
    webhooks,
    workflows,
)
```

Add to the route registration (after line 43):
```python
    app.include_router(projects.router)
```

- [ ] **Step 4: Write route tests**

```python
# tests/unit/test_projects_route.py
"""Tests for project API routes."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agent_fleet.main import create_app

TEST_USER = {"id": "user-123", "email": "test@example.com"}


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    from agent_fleet.api.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_repo():
    with patch("agent_fleet.api.routes.projects._get_repo") as mock:
        repo = MagicMock()
        mock.return_value = repo
        yield repo


class TestListProjects:
    def test_returns_user_projects(self, client, mock_repo):
        mock_repo.list_by_user.return_value = [
            {"id": "p1", "name": "Proj 1", "repo_path": "/tmp/a", "languages": [],
             "frameworks": [], "test_frameworks": [], "databases": [],
             "has_ci": False, "ci_platform": None, "has_docker": False,
             "estimated_loc": None, "created_at": "2026-03-29T00:00:00Z",
             "updated_at": "2026-03-29T00:00:00Z"},
        ]
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_empty_list(self, client, mock_repo):
        mock_repo.list_by_user.return_value = []
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateProject:
    def test_creates_project(self, client, mock_repo):
        mock_repo.create.return_value = {
            "id": "p-new", "name": "New", "repo_path": "/tmp/new",
            "languages": ["python"], "frameworks": [], "test_frameworks": [],
            "databases": [], "has_ci": False, "ci_platform": None,
            "has_docker": False, "estimated_loc": None,
            "created_at": "2026-03-29T00:00:00Z", "updated_at": "2026-03-29T00:00:00Z",
        }
        resp = client.post("/api/v1/projects", json={
            "name": "New", "repo_path": "/tmp/new", "languages": ["python"],
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "New"

    def test_missing_name_returns_422(self, client, mock_repo):
        resp = client.post("/api/v1/projects", json={"repo_path": "/tmp"})
        assert resp.status_code == 422


class TestGetProject:
    def test_returns_project_with_task_count(self, client, mock_repo):
        mock_repo.get.return_value = {
            "id": "p1", "user_id": "user-123", "name": "Proj",
            "repo_path": "/tmp", "languages": [], "frameworks": [],
            "test_frameworks": [], "databases": [], "has_ci": False,
            "ci_platform": None, "has_docker": False, "estimated_loc": None,
            "created_at": "2026-03-29T00:00:00Z", "updated_at": "2026-03-29T00:00:00Z",
        }
        with patch("agent_fleet.api.routes.projects.get_supabase_client") as mock_client:
            mock_task_result = MagicMock()
            mock_task_result.count = 5
            mock_client.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_task_result
            resp = client.get("/api/v1/projects/p1")

        assert resp.status_code == 200
        assert resp.json()["task_count"] == 5

    def test_404_for_missing(self, client, mock_repo):
        mock_repo.get.return_value = None
        resp = client.get("/api/v1/projects/nonexistent")
        assert resp.status_code == 404

    def test_404_for_other_user(self, client, mock_repo):
        mock_repo.get.return_value = {"id": "p1", "user_id": "other-user"}
        resp = client.get("/api/v1/projects/p1")
        assert resp.status_code == 404


class TestUpdateProject:
    def test_updates_project(self, client, mock_repo):
        mock_repo.get.return_value = {"id": "p1", "user_id": "user-123"}
        mock_repo.update.return_value = {
            "id": "p1", "name": "Updated", "repo_path": "/tmp",
            "languages": [], "frameworks": [], "test_frameworks": [],
            "databases": [], "has_ci": False, "ci_platform": None,
            "has_docker": False, "estimated_loc": None,
            "created_at": "2026-03-29T00:00:00Z", "updated_at": "2026-03-29T00:00:00Z",
        }
        resp = client.put("/api/v1/projects/p1", json={"name": "Updated"})
        assert resp.status_code == 200

    def test_empty_update_returns_400(self, client, mock_repo):
        mock_repo.get.return_value = {"id": "p1", "user_id": "user-123"}
        resp = client.put("/api/v1/projects/p1", json={})
        assert resp.status_code == 400


class TestDeleteProject:
    def test_deletes_project(self, client, mock_repo):
        mock_repo.get.return_value = {"id": "p1", "user_id": "user-123"}
        resp = client.delete("/api/v1/projects/p1")
        assert resp.status_code == 204
        mock_repo.delete.assert_called_once_with("p1")

    def test_404_for_other_user(self, client, mock_repo):
        mock_repo.get.return_value = {"id": "p1", "user_id": "other-user"}
        resp = client.delete("/api/v1/projects/p1")
        assert resp.status_code == 404
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/test_projects_route.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/agent_fleet/api/schemas/projects.py src/agent_fleet/api/routes/projects.py src/agent_fleet/main.py tests/unit/test_projects_route.py
git commit -m "feat(api): add /api/v1/projects CRUD routes (#185)"
```

---

## Task 4: Wire `project_id` Through Tasks

**Files:**
- Modify: `src/agent_fleet/store/supabase_repo.py` (SupabaseTaskRepository.create)
- Modify: `src/agent_fleet/api/routes/tasks.py` (submit_task, list_tasks)
- Modify: `src/agent_fleet/api/schemas/tasks.py` (TaskResponse)

- [ ] **Step 1: Update TaskRepository.create to accept project_id**

In `supabase_repo.py`, update `SupabaseTaskRepository.create` (line 18-36):

Change the method signature to:
```python
    def create(
        self,
        task_id: str,
        user_id: str,
        repo_path: str,
        description: str,
        workflow: str,
        project_id: str | None = None,
    ) -> dict:
```

And in the insert dict, add:
```python
"project_id": project_id,
```

- [ ] **Step 2: Update tasks route to pass project_id**

In `tasks.py`, update `submit_task` (line 30-36) to pass `project_id`:

```python
    task = repo.create(
        task_id=task_id,
        user_id=user["id"],
        repo_path=request.repo,
        description=request.description,
        workflow=str(request.workflow_id),
        project_id=request.project_id,
    )
```

- [ ] **Step 3: Add project_id filter to list_tasks**

Update `list_tasks` in `tasks.py` to accept optional query param:

```python
from fastapi import APIRouter, Depends, HTTPException, Query

@router.get("", response_model=TaskListResponse)
async def list_tasks(
    user: dict = Depends(get_current_user),
    repo: SupabaseTaskRepository = Depends(_get_repo),
    project_id: str | None = Query(None),
) -> TaskListResponse:
    """List tasks, optionally filtered by project."""
    if project_id:
        tasks = repo.list_by_project(user["id"], project_id)
    else:
        tasks = repo.list_by_user(user["id"])
    return TaskListResponse(tasks=[TaskResponse(**t) for t in tasks])
```

- [ ] **Step 4: Add list_by_project and count_by_project to TaskRepository**

Add to `SupabaseTaskRepository`:

```python
    def count_by_project(self, project_id: str) -> int:
        """Count tasks for a project."""
        result = (
            self._client.table("tasks")
            .select("id", count="exact")
            .eq("project_id", project_id)
            .execute()
        )
        return result.count or 0

    def list_by_project(self, user_id: str, project_id: str) -> list[dict]:
        """List tasks for a project, scoped to user."""
        result = (
            self._client.table("tasks")
            .select("*")
            .eq("user_id", user_id)
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
```

- [ ] **Step 5: Add project_id to TaskResponse schema**

In `src/agent_fleet/api/schemas/tasks.py`, add to `TaskResponse`:

```python
    project_id: str | None = None
```

- [ ] **Step 6: Add project_id tests to test_api_tasks.py**

Add these tests to the existing `tests/unit/test_api_tasks.py`:

```python
class TestSubmitWithProject:
    def test_submit_with_project_id(self, client, mock_repo):
        """POST /api/v1/tasks with project_id stores it."""
        mock_repo.create.return_value = {
            "id": "task-proj", "repo": "/tmp/repo", "description": "Task",
            "status": "queued", "workflow_name": "default", "project_id": "proj-1",
            "created_at": "2026-03-30T00:00:00Z", "updated_at": "2026-03-30T00:00:00Z",
        }
        response = client.post("/api/v1/tasks", json={
            "repo": "/tmp/repo", "description": "Task", "workflow_id": "wf-1",
            "project_id": "proj-1",
        })
        assert response.status_code == 201
        # Verify project_id was passed to create
        call_kwargs = mock_repo.create.call_args
        assert "proj-1" in str(call_kwargs)


class TestListByProject:
    def test_list_with_project_filter(self, client, mock_repo):
        """GET /api/v1/tasks?project_id=X filters by project."""
        mock_repo.list_by_project.return_value = [
            {"id": "t-1", "repo": "/tmp", "description": "Task", "status": "completed",
             "project_id": "proj-1", "created_at": "2026-03-30T00:00:00Z",
             "updated_at": "2026-03-30T00:00:00Z"},
        ]
        response = client.get("/api/v1/tasks?project_id=proj-1")
        assert response.status_code == 200
        mock_repo.list_by_project.assert_called_once()

    def test_list_without_project_filter(self, client, mock_repo):
        """GET /api/v1/tasks without project_id returns all user tasks."""
        mock_repo.list_by_user.return_value = []
        response = client.get("/api/v1/tasks")
        assert response.status_code == 200
        mock_repo.list_by_user.assert_called_once()
```

- [ ] **Step 7: Run all task tests**

Run: `pytest tests/unit/test_api_tasks.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/agent_fleet/store/supabase_repo.py src/agent_fleet/api/routes/tasks.py src/agent_fleet/api/schemas/tasks.py tests/unit/test_api_tasks.py
git commit -m "feat(api): wire project_id through task creation and listing (#185)"
```

---

## Task 5: UI — Project Cards Edit/Delete

**Files:**
- Modify: `fleet-ui/src/pages/Projects/Projects.tsx`

- [ ] **Step 1: Add edit/delete actions to project cards**

Read the current `Projects.tsx` fully. Add to each project card:
- An **edit icon button** that navigates to `/projects/${project.id}`
- A **delete icon button** that shows a confirmation dialog, then calls `DELETE /api/v1/projects/${project.id}` via fetch with auth token (same pattern as SubmitTask), and refreshes the list

Import `IconButton`, `EditOutlined`, `DeleteOutline` from MUI.
Import `useNavigate` from react-router-dom.

Add a confirmation dialog state (`deleteConfirmId`) and dialog component.

- [ ] **Step 2: Commit**

```bash
git add fleet-ui/src/pages/Projects/Projects.tsx
git commit -m "feat(ui): add edit/delete actions to project cards (#185)"
```

---

## Task 6: UI — Project Detail Page

**Files:**
- Create: `fleet-ui/src/pages/ProjectDetail/ProjectDetail.tsx`
- Modify: `fleet-ui/src/App.tsx` (add route + import)

- [ ] **Step 1: Create ProjectDetail page**

```tsx
// fleet-ui/src/pages/ProjectDetail/ProjectDetail.tsx
```

The page should:
1. Fetch project from `GET /api/v1/projects/:id` (via API with auth token)
2. Fetch project tasks from `GET /api/v1/tasks?project_id=:id` (via API with auth token)
3. Show project metadata: name, repo_path, languages, frameworks, test_frameworks, databases, LOC, CI info
4. Editable fields: name, repo_path — save via `PUT /api/v1/projects/:id`
5. Delete button with confirmation dialog — `DELETE /api/v1/projects/:id` → navigate to `/projects`
6. Task history table: description, status (badge), created_at, link to `/tasks/:id`
7. "New Task" button → navigates to `/submit?project_id=X&repo=Y`

Use MUI components: `Container`, `Typography`, `Card`, `Table`, `Chip` (for status badges), `Button`, `TextField`, `IconButton`, `Dialog`.

Use the existing auth token pattern from SubmitTask:
```tsx
const token = (await supabase.auth.getSession()).data.session?.access_token;
const response = await fetch(`${API_URL}/api/v1/projects/${id}`, {
  headers: { 'Authorization': `Bearer ${token}` },
});
```

- [ ] **Step 2: Add route to App.tsx**

Add import:
```tsx
import ProjectDetail from './pages/ProjectDetail/ProjectDetail';
```

Add route (near the `/projects` route):
```tsx
<Route path="/projects/:id" element={<ProtectedRoute><ProjectDetail /></ProtectedRoute>} />
```

- [ ] **Step 3: Commit**

```bash
git add fleet-ui/src/pages/ProjectDetail/ProjectDetail.tsx fleet-ui/src/App.tsx
git commit -m "feat(ui): add project detail page with task history (#185)"
```

---

## Task 7: UI — SubmitTask Project Selector

**Files:**
- Modify: `fleet-ui/src/pages/SubmitTask/SubmitTask.tsx`

- [ ] **Step 1: Add project selector**

Read current `SubmitTask.tsx`. Add:

1. A `projects` state and fetch from `GET /api/v1/projects` on mount
2. A `projectId` state initialized from URL param `?project_id=`
3. A `FormControl` + `Select` dropdown above the repo field labeled "Project (optional)"
4. When a project is selected: set `repo` to `project.repo_path`, set `projectId`
5. When "None" is selected: clear `projectId`, don't change repo
6. Send `project_id: projectId` in the API call body (alongside existing fields)
7. Read URL search params on mount: `const params = new URLSearchParams(location.search)` — pre-fill `projectId` and `repo` from `project_id` and `repo` params

Import `useLocation` from react-router-dom for URL params.

- [ ] **Step 2: Commit**

```bash
git add fleet-ui/src/pages/SubmitTask/SubmitTask.tsx
git commit -m "feat(ui): add project selector to SubmitTask form (#185)"
```

---

## Task 8: Final Integration — Verify Full Test Suite

**Files:**
- All modified and new files

- [ ] **Step 1: Run lint**

Run: `ruff check src/ cli/ tests/`

- [ ] **Step 2: Run format**

Run: `ruff format src/ cli/ tests/`

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/unit/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 4: Fix any issues**

- [ ] **Step 5: Commit if fixes needed**

```bash
git add -A
git commit -m "fix: lint and test fixes for project CRUD (#185)"
```

---

## Execution Order

```
Task 1 (migration) ─┐
                     ├─→ Task 3 (API routes + schemas) ─→ Task 4 (wire project_id)
Task 2 (project repo)┘                                           ↓
                                               Task 5 + Task 6 + Task 7 (UI, parallel)
                                                                  ↓
                                                           Task 8 (final verify)
```

**Parallelizable:**
- Tasks 1 and 2 can start immediately (no deps on each other)
- Task 3 depends on Task 2 (imports SupabaseProjectRepository)
- Task 4 depends on Task 3 (needs routes registered for project_id tests)
- Tasks 5, 6, 7 can run in parallel after Task 4
- Task 8 runs last
