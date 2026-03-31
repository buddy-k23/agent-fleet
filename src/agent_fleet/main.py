"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_fleet import __version__
from agent_fleet.api.routes import (
    agents,
    api_keys,
    approvals,
    audit,
    chat,
    profile,
    projects,
    tasks,
    webhooks,
    workflows,
)
from agent_fleet.api.schemas import HealthResponse


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Agent Fleet", version=__version__)

    # CORS for React UI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(tasks.router)
    app.include_router(projects.router)
    app.include_router(agents.router)
    app.include_router(workflows.router)
    app.include_router(profile.router)
    app.include_router(webhooks.router)
    app.include_router(chat.router)
    app.include_router(api_keys.router)
    app.include_router(approvals.router)
    app.include_router(audit.router)

    @app.get("/health")
    def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    return app


# Default app for uvicorn
app = create_app()
