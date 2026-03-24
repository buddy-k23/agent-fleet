"""Task API routes — submit, list, get, cancel tasks."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException

from agent_fleet.api.deps import get_current_user, get_supabase_client
from agent_fleet.api.schemas.tasks import TaskListResponse, TaskResponse, TaskSubmitRequest
from agent_fleet.store.supabase_repo import SupabaseTaskRepository

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _get_repo() -> SupabaseTaskRepository:
    client = get_supabase_client()
    return SupabaseTaskRepository(client)


@router.post("", status_code=201, response_model=TaskResponse)
async def submit_task(
    request: TaskSubmitRequest,
    user: dict = Depends(get_current_user),
    repo: SupabaseTaskRepository = Depends(_get_repo),
) -> TaskResponse:
    """Submit a new task for orchestrator execution."""
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    task = repo.create(
        task_id=task_id,
        user_id=user["id"],
        repo_path=request.repo,
        description=request.description,
        workflow=str(request.workflow_id),
    )

    logger.info("task_submitted", task_id=task_id, user_id=user["id"])
    return TaskResponse(**task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    user: dict = Depends(get_current_user),
    repo: SupabaseTaskRepository = Depends(_get_repo),
) -> TaskListResponse:
    """List all tasks for the current user."""
    tasks = repo.list_by_user(user["id"])
    return TaskListResponse(tasks=[TaskResponse(**t) for t in tasks])


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    repo: SupabaseTaskRepository = Depends(_get_repo),
) -> TaskResponse:
    """Get task details by ID — scoped to current user."""
    task = repo.get(task_id)
    if not task or task.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task)


@router.delete("/{task_id}/cancel", status_code=200)
async def cancel_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    repo: SupabaseTaskRepository = Depends(_get_repo),
) -> dict:
    """Cancel a running or queued task — scoped to current user."""
    task = repo.get(task_id)
    if not task or task.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in ("queued", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task with status '{task['status']}'")

    repo.update_status(task_id, "cancelled")
    logger.info("task_cancelled", task_id=task_id, user_id=user["id"])
    return {"status": "cancelled", "task_id": task_id}
