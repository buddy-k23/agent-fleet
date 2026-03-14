"""Event logging helpers for the orchestrator."""

from typing import Any

import structlog

logger = structlog.get_logger()


def log_event(task_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Create and log an event. Returns the event dict."""
    event: dict[str, Any] = {
        "task_id": task_id,
        "event_type": event_type,
        "payload": payload,
    }
    logger.info("fleet_event", **event)
    return event
