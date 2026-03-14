"""Task submission and management routes."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from agent_fleet.api.schemas import TaskListResponse, TaskResponse, TaskSubmitRequest
from agent_fleet.store.models import TaskRecord
from agent_fleet.store.repository import TaskRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _get_session(request: Request) -> Session:  # type: ignore[misc]
    yield from request.app.state.get_session()


def _task_to_response(task: TaskRecord) -> TaskResponse:
    return TaskResponse(
        task_id=task.id,
        repo=task.repo,
        description=task.description,
        status=task.status,
        workflow=task.workflow,
    )


@router.post("", status_code=201, response_model=TaskResponse)
def submit_task(
    request: TaskSubmitRequest,
    session: Session = Depends(_get_session),
) -> TaskResponse:
    """Submit a new task to the fleet."""
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    repo = TaskRepository(session)
    task = repo.create(
        task_id=task_id,
        repo_path=request.repo,
        description=request.description,
        workflow=request.workflow,
    )
    logger.info("task_submitted", task_id=task_id, repo=request.repo)
    return _task_to_response(task)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    session: Session = Depends(_get_session),
) -> TaskResponse:
    """Get a task by ID."""
    repo = TaskRepository(session)
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@router.get("", response_model=TaskListResponse)
def list_tasks(
    session: Session = Depends(_get_session),
) -> TaskListResponse:
    """List all tasks."""
    repo = TaskRepository(session)
    tasks = repo.list_all()
    return TaskListResponse(tasks=[_task_to_response(t) for t in tasks])
