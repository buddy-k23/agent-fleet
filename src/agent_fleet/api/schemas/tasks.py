"""Pydantic schemas for task API endpoints."""

from datetime import datetime

from pydantic import BaseModel


class TaskSubmitRequest(BaseModel):
    """Request body for POST /api/v1/tasks."""

    repo: str
    description: str
    workflow_id: str
    project_id: str | None = None


class TaskResponse(BaseModel):
    """Response body for task endpoints."""

    id: str
    repo: str
    description: str
    status: str
    project_id: str | None = None
    workflow_name: str | None = None
    current_stage: str | None = None
    completed_stages: list[str] = []
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    pr_url: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """Response body for GET /api/v1/tasks."""

    tasks: list[TaskResponse]
