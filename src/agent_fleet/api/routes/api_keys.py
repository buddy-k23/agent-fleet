"""API key management routes."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agent_fleet.api.auth import get_current_user
from agent_fleet.store.api_keys import (
    delete_api_key,
    get_api_key,
    list_api_keys,
    store_api_key,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


class AddKeyRequest(BaseModel):
    provider: str
    api_key: str
    label: str = ""


@router.get("")
def list_keys(user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    """List API keys (masked)."""
    return list_api_keys(user["id"])


@router.post("", status_code=201)
def add_key(
    req: AddKeyRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Add a new API key."""
    if req.provider not in ("anthropic", "openai", "google", "ollama"):
        raise HTTPException(status_code=400, detail="Invalid provider")

    result = store_api_key(user["id"], req.provider, req.api_key, req.label)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to store key")

    return {"id": result["id"], "provider": req.provider, "status": "stored"}


@router.delete("/{key_id}", status_code=204)
def remove_key(
    key_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete an API key."""
    delete_api_key(key_id)


@router.post("/{key_id}/test")
def test_key(
    key_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Test if an API key works."""
    keys = list_api_keys(user["id"])
    key_info = next((k for k in keys if k["id"] == key_id), None)
    if not key_info:
        raise HTTPException(status_code=404, detail="Key not found")

    provider = key_info["provider"]
    decrypted = get_api_key(user["id"], provider)
    if not decrypted:
        return {"status": "error", "message": "Could not decrypt key"}

    # Test by making a minimal API call
    try:
        if provider == "anthropic":
            import httpx

            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": decrypted,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
                timeout=10,
            )
            if r.status_code == 200:
                return {"status": "ok", "message": "Key works"}
            return {"status": "error", "message": f"API returned {r.status_code}"}

        elif provider == "openai":
            import httpx

            r = httpx.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {decrypted}"},
                timeout=10,
            )
            if r.status_code == 200:
                return {"status": "ok", "message": "Key works"}
            return {"status": "error", "message": f"API returned {r.status_code}"}

        elif provider == "ollama":
            import httpx

            base = decrypted if decrypted.startswith("http") else "http://localhost:11434"
            r = httpx.get(f"{base}/api/tags", timeout=5)
            if r.status_code == 200:
                return {"status": "ok", "message": "Ollama connected"}
            return {"status": "error", "message": "Ollama not reachable"}

        return {"status": "unknown", "message": f"No test for {provider}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
