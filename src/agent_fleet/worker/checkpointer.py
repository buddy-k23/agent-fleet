"""Checkpointer factory — creates PostgresSaver for LangGraph crash recovery."""

import os

import structlog
from langgraph.checkpoint.postgres import PostgresSaver

logger = structlog.get_logger()


def get_checkpointer() -> PostgresSaver:
    """Create a Postgres checkpointer using Supabase's direct DB connection.

    Requires SUPABASE_DB_URL env var (direct Postgres connection string,
    not the REST API URL). Available in Supabase dashboard under
    Project Settings > Database > Connection string.
    """
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError(
            "SUPABASE_DB_URL not configured: set to direct Postgres connection string "
            "(e.g., postgresql://postgres:password@db.xxx.supabase.co:5432/postgres)"
        )

    saver = PostgresSaver.from_conn_string(db_url)
    saver.setup()
    logger.info("checkpointer_ready", backend="postgres")
    return saver
