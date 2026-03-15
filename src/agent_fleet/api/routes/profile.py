"""Profile and preferences routes."""

from typing import Any

from fastapi import APIRouter, Depends

from agent_fleet.api.auth import get_current_user
from agent_fleet.store.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("")
def get_profile(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    client = get_supabase_client()
    if not client:
        return {"id": user["id"], "display_name": user["email"], "preferences": {}}

    result = client.table("profiles").select("*").eq("id", user["id"]).execute()
    if result.data:
        return result.data[0]
    return {"id": user["id"], "display_name": user["email"], "preferences": {}}


@router.put("")
def update_profile(
    profile_data: dict[str, Any],
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    client = get_supabase_client()
    if not client:
        return profile_data

    allowed = {"display_name", "default_workflow", "preferences"}
    filtered = {k: v for k, v in profile_data.items() if k in allowed}

    result = (
        client.table("profiles")
        .update(filtered)
        .eq("id", user["id"])
        .execute()
    )
    return result.data[0] if result.data else {}
