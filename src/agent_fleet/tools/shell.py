"""Shell tool — sandboxed command execution within workspace."""

import subprocess
from pathlib import Path
from typing import Any

import structlog

from agent_fleet.tools.base import BaseTool

logger = structlog.get_logger()


class ShellTool(BaseTool):
    """Run shell commands scoped to the workspace directory."""

    def __init__(self, workspace_root: Path, timeout_seconds: int = 120) -> None:
        self._root = workspace_root
        self._timeout = timeout_seconds

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return "Run a shell command in the workspace directory"

    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        command = input["command"]
        logger.info("shell_execute", command=command, cwd=str(self._root))
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            logger.warning(
                "shell_timeout", command=command, timeout=self._timeout
            )
            return {
                "error": f"Command timed out after {self._timeout}s",
                "returncode": -1,
            }

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run",
                },
            },
            "required": ["command"],
        }
