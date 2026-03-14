"""FastAPI application factory."""

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from agent_fleet import __version__
from agent_fleet.api.schemas import HealthResponse
from agent_fleet.store.models import Base


def create_app(database_url: str = "sqlite:///./agent_fleet.db") -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Agent Fleet", version=__version__)

    # Database setup
    engine = create_engine(database_url)
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

    @app.get("/health")
    def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    return app


# Default app for uvicorn
app = create_app()
