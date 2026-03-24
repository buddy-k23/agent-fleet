"""Supabase client factories and auth dependency for FastAPI routes."""

import os
from functools import lru_cache

import structlog
from fastapi import HTTPException, Request
from supabase import Client, create_client

logger = structlog.get_logger()


@lru_cache(maxsize=1)
def _get_anon_client() -> Client:
    """Cached anon client — created once per process."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Supabase not configured: set SUPABASE_URL and SUPABASE_ANON_KEY")
    return create_client(url, key)


def get_supabase_client() -> Client:
    """Anon client for API routes — RLS enforced via JWT.

    Note: For RLS to scope queries to the user, the caller must also
    use get_current_user and filter by user_id. The anon key enables
    RLS policies but doesn't automatically carry the user's JWT.
    Routes MUST filter by user_id for defense-in-depth.
    """
    return _get_anon_client()


@lru_cache(maxsize=1)
def get_service_client() -> Client:
    """Service role client for worker — bypasses RLS."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Supabase service role not configured: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
        )
    return create_client(url, key)


async def get_current_user(request: Request) -> dict:
    """Validate JWT from Authorization header, return user dict."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.removeprefix("Bearer ")
    try:
        client = get_supabase_client()
        user_response = client.auth.get_user(token)
        user = user_response.user
        return {"id": str(user.id), "email": user.email}
    except Exception as e:
        logger.warning("auth_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired token")
