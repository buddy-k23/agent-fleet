"""Database engine and session factory."""

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def get_engine(url: str | None = None) -> Engine:
    """Create SQLAlchemy engine from URL or DATABASE_URL env var."""
    db_url = url or os.getenv("DATABASE_URL", "sqlite:///./agent_fleet.db")
    return create_engine(db_url, echo=False)


def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    """Create session factory bound to an engine."""
    engine = get_engine(url)
    return sessionmaker(bind=engine)
