"""Supabase client initialization for Python backend."""

import os

import structlog

from supabase import Client, create_client

logger = structlog.get_logger()

_client: Client | None = None


def get_supabase_client() -> Client | None:
    """Get or create the Supabase client. Returns None if not configured."""
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        logger.info("supabase_not_configured", reason="Missing SUPABASE_URL or key")
        return None

    _client = create_client(url, key)
    logger.info("supabase_client_created", url=url)
    return _client


def is_supabase_configured() -> bool:
    """Check if Supabase environment variables are set."""
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))
