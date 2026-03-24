"""Supabase Storage — upload/download agent outputs and logs."""

import json

import structlog

from agent_fleet.api.deps import get_supabase_client

logger = structlog.get_logger()


def upload_stage_output(task_id: str, stage: str, output: dict) -> str | None:
    """Upload stage output JSON to Supabase Storage."""
    client = get_supabase_client()
    if not client:
        return None

    path = f"{task_id}/{stage}.json"
    content = json.dumps(output, indent=2).encode()

    try:
        client.storage.from_("task-outputs").upload(path, content, {
            "content-type": "application/json",
            "upsert": "true",
        })
        logger.info("storage_upload", bucket="task-outputs", path=path)
        return path
    except Exception as e:
        logger.warning("storage_upload_failed", path=path, error=str(e))
        return None


def upload_task_log(task_id: str, events: list[dict]) -> str | None:
    """Upload full event log for a task."""
    client = get_supabase_client()
    if not client:
        return None

    path = f"{task_id}/events.json"
    content = json.dumps(events, indent=2, default=str).encode()

    try:
        client.storage.from_("task-logs").upload(path, content, {
            "content-type": "application/json",
            "upsert": "true",
        })
        logger.info("storage_upload", bucket="task-logs", path=path)
        return path
    except Exception as e:
        logger.warning("storage_upload_failed", path=path, error=str(e))
        return None


def get_download_url(bucket: str, path: str, expires_in: int = 3600) -> str | None:
    """Get a signed download URL for a storage object."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        result = client.storage.from_(bucket).create_signed_url(path, expires_in)
        return result.get("signedURL")
    except Exception as e:
        logger.warning("storage_url_failed", bucket=bucket, path=path, error=str(e))
        return None
