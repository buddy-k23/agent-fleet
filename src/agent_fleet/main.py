"""FastAPI application factory."""

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_fleet import __version__
from agent_fleet.api.routes import tasks
from agent_fleet.api.schemas import HealthResponse
from agent_fleet.store.models import Base


def create_app(database_url: str = "sqlite:///./agent_fleet.db") -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Agent Fleet", version=__version__)

    # Database setup — StaticPool for in-memory SQLite (tests), default pool otherwise
    connect_args: dict = {}
    kwargs: dict = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if ":memory:" in database_url:
            kwargs["poolclass"] = StaticPool
    engine = create_engine(database_url, connect_args=connect_args, **kwargs)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def get_session() -> Session:  # type: ignore[misc]
        session = session_factory()
        try:
            yield session  # type: ignore[misc]
        finally:
            session.close()

    # Store session dependency for route modules to use
    app.state.get_session = get_session

    # Routes
    app.include_router(tasks.router)

    @app.get("/health")
    def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    return app


# Default app for uvicorn
app = create_app()
