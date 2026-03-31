"""Project CRUD routes backed by Supabase."""

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
