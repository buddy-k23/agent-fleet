"""Code tools — file read, write, list with path sandboxing."""

from pathlib import Path
from typing import Any

from agent_fleet.tools.base import BaseTool


class ReadFileTool(BaseTool):
    """Read the contents of a file within the workspace."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file"

    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        target = self._validate_path(self._root, input["path"])
        if target is None:
            return {"error": "Path is outside workspace"}
        if not target.exists():
            return {"error": f"File not found: {input['path']}"}
        return {"content": target.read_text()}

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace"},
            },
            "required": ["path"],
        }


class WriteFileTool(BaseTool):
    """Write content to a file within the workspace."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file"

    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        target = self._validate_path(self._root, input["path"])
        if target is None:
            return {"error": "Path is outside workspace"}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(input["content"])
        return {"success": True, "path": str(target.relative_to(self._root))}

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        }


class ListFilesTool(BaseTool):
    """List files in a directory within the workspace."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files in a directory"

    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        target_dir = self._validate_path(self._root, input.get("path", "."))
        if target_dir is None:
            return {"error": "Path is outside workspace"}
        if not target_dir.is_dir():
            return {"error": f"Not a directory: {input.get('path', '.')}"}
        files = [
            str(f.relative_to(self._root))
            for f in sorted(target_dir.rglob("*"))
            if f.is_file()
        ]
        return {"files": files[:500]}

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to workspace, default '.'",
                },
            },
        }
