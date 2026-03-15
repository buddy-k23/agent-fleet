"""Supabase auth middleware for FastAPI."""


import structlog
from fastapi import HTTPException, Request

from agent_fleet.store.supabase_client import get_supabase_client

logger = structlog.get_logger()


async def get_current_user(request: Request) -> dict:
    """Extract and validate user from Supabase JWT token.

    Returns dict with 'id' and 'email' keys.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ", 1)[1]

    client = get_supabase_client()
    if not client:
        # No Supabase configured — allow anonymous for local dev
        logger.warning("auth_bypass", reason="Supabase not configured")
        return {"id": "local-dev", "email": "dev@localhost"}

    try:
        user_response = client.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {
            "id": str(user_response.user.id),
            "email": user_response.user.email or "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("auth_validation_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Token validation failed")
