"""Pydantic schemas for API endpoints."""

from pydantic import BaseModel

from agent_fleet.api.schemas.tasks import TaskListResponse, TaskResponse, TaskSubmitRequest


class HealthResponse(BaseModel):
    """Response body for health check."""

    status: str = "ok"
    version: str


__all__ = [
    "HealthResponse",
    "TaskListResponse",
    "TaskResponse",
    "TaskSubmitRequest",
]
