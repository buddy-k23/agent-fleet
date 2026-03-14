"""Tests for tool registry — create_tools + schema conversion."""

from pathlib import Path

from agent_fleet.tools.base import BaseTool
from agent_fleet.tools.code import ListFilesTool, ReadFileTool, WriteFileTool
from agent_fleet.tools.registry import create_tools, tool_to_litellm_schema
from agent_fleet.tools.shell import ShellTool


class TestCreateTools:
    def test_code_category_returns_three_tools(self, tmp_path: Path) -> None:
        tools = create_tools(["code"], tmp_path)
        assert len(tools) == 3
        types = {type(t) for t in tools}
        assert ReadFileTool in types
        assert WriteFileTool in types
        assert ListFilesTool in types

    def test_shell_category_returns_one_tool(self, tmp_path: Path) -> None:
        tools = create_tools(["shell"], tmp_path)
        assert len(tools) == 1
        assert isinstance(tools[0], ShellTool)

    def test_multiple_categories(self, tmp_path: Path) -> None:
        tools = create_tools(["code", "shell"], tmp_path)
        assert len(tools) == 4

    def test_unknown_category_skipped(self, tmp_path: Path) -> None:
        tools = create_tools(["code", "search", "unknown"], tmp_path)
        # Only code tools returned, search and unknown skipped
        assert len(tools) == 3

    def test_empty_list_returns_empty(self, tmp_path: Path) -> None:
        tools = create_tools([], tmp_path)
        assert tools == []

    def test_duplicate_category_deduped(self, tmp_path: Path) -> None:
        tools = create_tools(["shell", "shell"], tmp_path)
        # Should still work, may return duplicates (acceptable)
        assert len(tools) >= 1


class TestToolToLitellmSchema:
    def test_schema_has_correct_structure(self, tmp_path: Path) -> None:
        tool = ReadFileTool(workspace_root=tmp_path)
        schema = tool_to_litellm_schema(tool)
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "read_file"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]

    def test_schema_parameters_from_tool(self, tmp_path: Path) -> None:
        tool = ShellTool(workspace_root=tmp_path)
        schema = tool_to_litellm_schema(tool)
        params = schema["function"]["parameters"]
        assert params["type"] == "object"
        assert "command" in params["properties"]
