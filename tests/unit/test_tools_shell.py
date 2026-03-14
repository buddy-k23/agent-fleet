"""Tests for ShellTool — sandboxed command execution."""

from pathlib import Path

from agent_fleet.tools.shell import ShellTool


class TestShellTool:
    def test_run_simple_command(self, tmp_path: Path) -> None:
        tool = ShellTool(workspace_root=tmp_path)
        result = tool.execute({"command": "echo hello"})
        assert "hello" in result["stdout"]
        assert result["returncode"] == 0

    def test_run_failing_command(self, tmp_path: Path) -> None:
        tool = ShellTool(workspace_root=tmp_path)
        result = tool.execute({"command": "false"})
        assert result["returncode"] != 0

    def test_cwd_is_workspace(self, tmp_path: Path) -> None:
        tool = ShellTool(workspace_root=tmp_path)
        result = tool.execute({"command": "pwd"})
        assert str(tmp_path) in result["stdout"]

    def test_captures_stderr(self, tmp_path: Path) -> None:
        tool = ShellTool(workspace_root=tmp_path)
        result = tool.execute({"command": "echo err >&2"})
        assert "err" in result["stderr"]

    def test_timeout_returns_error(self, tmp_path: Path) -> None:
        tool = ShellTool(workspace_root=tmp_path, timeout_seconds=1)
        result = tool.execute({"command": "sleep 10"})
        assert "error" in result
        assert result["returncode"] == -1

    def test_schema_has_command(self, tmp_path: Path) -> None:
        tool = ShellTool(workspace_root=tmp_path)
        s = tool.schema()
        assert "command" in s["properties"]
        assert "command" in s["required"]

    def test_name_and_description(self, tmp_path: Path) -> None:
        tool = ShellTool(workspace_root=tmp_path)
        assert tool.name == "shell"
        assert len(tool.description) > 0
