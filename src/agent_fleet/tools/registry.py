"""Tool registry — map tool category names to concrete tool instances."""

from pathlib import Path
from typing import Any

import structlog

from agent_fleet.tools.base import BaseTool
from agent_fleet.tools.code import ListFilesTool, ReadFileTool, WriteFileTool
from agent_fleet.tools.shell import ShellTool

logger = structlog.get_logger()


def create_tools(tool_names: list[str], worktree_path: Path) -> list[BaseTool]:
    """Map tool category names to instantiated tools scoped to a worktree.

    Unknown categories are logged and skipped.
    """
    tools: list[BaseTool] = []
    for name in tool_names:
        if name == "code":
            tools.extend([
                ReadFileTool(workspace_root=worktree_path),
                WriteFileTool(workspace_root=worktree_path),
                ListFilesTool(workspace_root=worktree_path),
            ])
        elif name == "shell":
            tools.append(ShellTool(workspace_root=worktree_path))
        else:
            logger.warning("unknown_tool_category", category=name)
    return tools


def tool_to_litellm_schema(tool: BaseTool) -> dict[str, Any]:
    """Convert a BaseTool to the OpenAI/LiteLLM function-calling format."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.schema(),
        },
    }
