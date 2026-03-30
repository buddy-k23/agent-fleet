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
