"""GitHub/GitLab webhook handlers."""

import hashlib
import hmac
import os
from typing import Any

import structlog
from fastapi import APIRouter, Header, HTTPException, Request

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


def _verify_github_signature(payload: bytes, signature: str | None) -> bool:
    """Verify GitHub webhook signature using HMAC-SHA256."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret or not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(None),
    x_hub_signature_256: str | None = Header(None),
) -> dict[str, Any]:
    """Receive GitHub webhook events."""
    body = await request.body()

    # Verify signature if secret is configured
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if secret and not _verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event_type = x_github_event or "unknown"

    logger.info("webhook_received", provider="github", event_type=event_type)

    if event_type == "issues" and payload.get("action") in ("opened", "labeled"):
        from agent_fleet.integrations.github import issue_to_task

        task_info = issue_to_task(payload)
        logger.info("webhook_task_created", task=task_info)
        return {"status": "accepted", "task": task_info}

    return {"status": "ignored", "event": event_type}
