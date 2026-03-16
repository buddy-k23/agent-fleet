"""Immutable audit log — tamper-proof event store for banking compliance."""

import structlog

from agent_fleet.store.supabase_client import get_supabase_client

logger = structlog.get_logger()


def log_audit_event(
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    actor_id: str | None = None,
    actor_email: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Write an immutable audit log entry. Cannot be updated or deleted."""
    client = get_supabase_client()
    if not client:
        logger.info("audit_event", action=action, resource_type=resource_type)
        return

    entry = {
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
    }
    if actor_id:
        entry["actor_id"] = actor_id
    if actor_email:
        entry["actor_email"] = actor_email
    if ip_address:
        entry["ip_address"] = ip_address

    try:
        client.table("audit_log").insert(entry).execute()
        logger.info("audit_logged", action=action, resource=resource_type)
    except Exception as e:
        logger.error("audit_log_failed", action=action, error=str(e))


def get_audit_log(
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    resource_type: str | None = None,
    actor_id: str | None = None,
) -> list[dict]:
    """Query audit log with optional filters."""
    client = get_supabase_client()
    if not client:
        return []

    query = client.table("audit_log").select("*").order("timestamp", desc=True)

    if action:
        query = query.eq("action", action)
    if resource_type:
        query = query.eq("resource_type", resource_type)
    if actor_id:
        query = query.eq("actor_id", actor_id)

    result = query.range(offset, offset + limit - 1).execute()
    return result.data
