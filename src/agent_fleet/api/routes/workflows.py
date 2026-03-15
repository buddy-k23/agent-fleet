"""Workflow CRUD routes backed by Supabase."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException

from agent_fleet.api.auth import get_current_user
from agent_fleet.store.supabase_client import get_supabase_client
from agent_fleet.store.supabase_repo import SupabaseWorkflowRepository

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


def _get_repo() -> SupabaseWorkflowRepository:
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase not configured")
    return SupabaseWorkflowRepository(client)


@router.get("")
def list_workflows(
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    repo = _get_repo()
    return repo.list_by_user(user["id"])


@router.get("/{workflow_id}")
def get_workflow(
    workflow_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    repo = _get_repo()
    wf = repo.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.post("", status_code=201)
def create_workflow(
    workflow_data: dict[str, Any],
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    repo = _get_repo()
    return repo.create(user["id"], workflow_data)


@router.put("/{workflow_id}")
def update_workflow(
    workflow_id: str,
    workflow_data: dict[str, Any],
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    repo = _get_repo()
    return repo.update(workflow_id, workflow_data)


@router.delete("/{workflow_id}", status_code=204)
def delete_workflow(
    workflow_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    repo = _get_repo()
    repo.delete(workflow_id)
