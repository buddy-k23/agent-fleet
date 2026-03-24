"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel


class TaskSubmitRequest(BaseModel):
    """Request body for submitting a new task."""

    repo: str
    description: str
    workflow: str = "default"


class TaskResponse(BaseModel):
    """Response body for a single task."""

    task_id: str
    repo: str
    description: str
    status: str
    workflow: str


class TaskListResponse(BaseModel):
    """Response body for listing tasks."""

    tasks: list[TaskResponse]


class HealthResponse(BaseModel):
    """Response body for health check."""

    status: str = "ok"
    version: str


class TaskDetailResponse(TaskResponse):
    """Extended response with pipeline progress."""

    current_stage: str | None = None
    completed_stages: list[str] = []
    total_tokens: int = 0
