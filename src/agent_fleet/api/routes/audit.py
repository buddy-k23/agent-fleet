"""Audit log routes."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from agent_fleet.api.deps import get_current_user
from agent_fleet.store.audit import get_audit_log

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("")
def list_audit_events(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Query the immutable audit log."""
    return get_audit_log(
        limit=limit,
        offset=offset,
        action=action,
        resource_type=resource_type,
    )
