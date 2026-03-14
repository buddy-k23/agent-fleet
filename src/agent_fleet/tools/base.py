"""Base tool interface for Agent Fleet."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseTool(ABC):
    """Abstract base for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used by the LLM."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description used by the LLM."""
        ...

    @abstractmethod
    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool and return results."""
        ...

    @abstractmethod
    def schema(self) -> dict[str, Any]:
        """JSON schema for the tool's parameters."""
        ...

    def _validate_path(self, workspace_root: Path, requested: str) -> Path | None:
        """Resolve a path and ensure it's within the workspace.

        Returns the resolved Path if valid, None if outside workspace.
        """
        resolved = (workspace_root / requested).resolve()
        if not str(resolved).startswith(str(workspace_root.resolve())):
            return None
        return resolved
