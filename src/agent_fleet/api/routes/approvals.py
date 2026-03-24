"""Approval routes for banking workflows."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agent_fleet.api.deps import get_current_user, get_supabase_client
from agent_fleet.store.audit import log_audit_event

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/tasks", tags=["approvals"])


class ApprovalRequest(BaseModel):
    decision: str  # "approved" or "rejected"
    reason: str = ""


@router.post("/{task_id}/approve")
def approve_task(
    task_id: str,
    req: ApprovalRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Approve or reject a task at its current approval gate."""
    if req.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    # Get current task
    task = client.table("tasks").select("*").eq("id", task_id).single().execute()
    if not task.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task_data = task.data
    if task_data.get("status") != "awaiting_approval":
        raise HTTPException(status_code=400, detail="Task is not awaiting approval")

    # Record approval
    client.table("approvals").insert({
        "task_id": task_id,
        "stage": task_data.get("current_stage", ""),
        "approver_id": user["id"],
        "approver_email": user["email"],
        "decision": req.decision,
        "reason": req.reason,
    }).execute()

    # Log to audit trail
    log_audit_event(
        action=f"approval_{req.decision}",
        resource_type="task",
        resource_id=task_id,
        actor_id=user["id"],
        actor_email=user["email"],
        details={
            "stage": task_data.get("current_stage"),
            "decision": req.decision,
            "reason": req.reason,
        },
    )

    # Update task status
    if req.decision == "approved":
        client.table("tasks").update({"status": "running"}).eq("id", task_id).execute()
        logger.info("task_approved", task_id=task_id, approver=user["email"])
        return {"status": "approved", "task_id": task_id}
    else:
        client.table("tasks").update({
            "status": "rejected",
            "error_message": f"Rejected by {user['email']}: {req.reason}",
        }).eq("id", task_id).execute()
        logger.info("task_rejected", task_id=task_id, approver=user["email"])
        return {"status": "rejected", "task_id": task_id, "reason": req.reason}


@router.get("/{task_id}/approvals")
def list_approvals(
    task_id: str,
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all approvals for a task."""
    client = get_supabase_client()
    if not client:
        return []

    result = (
        client.table("approvals")
        .select("*")
        .eq("task_id", task_id)
        .order("created_at")
        .execute()
    )
    return result.data
