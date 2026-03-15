"""Agent CRUD routes backed by Supabase."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends

from agent_fleet.api.auth import get_current_user
from agent_fleet.store.supabase_client import get_supabase_client
from agent_fleet.store.supabase_repo import SupabaseAgentRepository

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def _get_repo() -> SupabaseAgentRepository:
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase not configured")
    return SupabaseAgentRepository(client)


@router.get("")
def list_agents(
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    repo = _get_repo()
    return repo.list_by_user(user["id"])


@router.post("", status_code=201)
def create_agent(
    agent_data: dict[str, Any],
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    repo = _get_repo()
    return repo.create(user["id"], agent_data)


@router.put("/{agent_id}")
def update_agent(
    agent_id: str,
    agent_data: dict[str, Any],
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    repo = _get_repo()
    return repo.update(agent_id, agent_data)


@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    agent_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    repo = _get_repo()
    repo.delete(agent_id)
