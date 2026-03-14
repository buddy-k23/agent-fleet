"""Tests for code tools — ReadFile, WriteFile, ListFiles."""

from pathlib import Path

from agent_fleet.tools.code import ListFilesTool, ReadFileTool, WriteFileTool


class TestReadFileTool:
    def test_read_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        tool = ReadFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "test.txt"})
        assert result["content"] == "hello world"

    def test_read_outside_workspace_blocked(self, tmp_path: Path) -> None:
        tool = ReadFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "/etc/passwd"})
        assert "error" in result

    def test_read_nonexistent_file(self, tmp_path: Path) -> None:
        tool = ReadFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "nope.txt"})
        assert "error" in result

    def test_read_traversal_blocked(self, tmp_path: Path) -> None:
        tool = ReadFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "../../etc/passwd"})
        assert "error" in result

    def test_schema_has_required_path(self) -> None:
        tool = ReadFileTool(workspace_root=Path("/tmp"))
        s = tool.schema()
        assert "path" in s["properties"]
        assert "path" in s["required"]


class TestWriteFileTool:
    def test_write_file(self, tmp_path: Path) -> None:
        tool = WriteFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "out.txt", "content": "written"})
        assert result["success"] is True
        assert (tmp_path / "out.txt").read_text() == "written"

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        tool = WriteFileTool(workspace_root=tmp_path)
        tool.execute({"path": "sub/dir/file.txt", "content": "deep"})
        assert (tmp_path / "sub" / "dir" / "file.txt").read_text() == "deep"

    def test_write_outside_workspace_blocked(self, tmp_path: Path) -> None:
        tool = WriteFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "/tmp/evil.txt", "content": "bad"})
        assert "error" in result

    def test_schema_has_required_fields(self) -> None:
        tool = WriteFileTool(workspace_root=Path("/tmp"))
        s = tool.schema()
        assert "path" in s["properties"]
        assert "content" in s["properties"]
        assert set(s["required"]) == {"path", "content"}


class TestListFilesTool:
    def test_list_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        tool = ListFilesTool(workspace_root=tmp_path)
        result = tool.execute({"path": "."})
        assert len(result["files"]) == 2

    def test_list_nested_files(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.txt").write_text("n")
        (tmp_path / "top.txt").write_text("t")
        tool = ListFilesTool(workspace_root=tmp_path)
        result = tool.execute({"path": "."})
        assert len(result["files"]) == 2

    def test_list_outside_workspace_blocked(self, tmp_path: Path) -> None:
        tool = ListFilesTool(workspace_root=tmp_path)
        result = tool.execute({"path": "/etc"})
        assert "error" in result

    def test_list_nonexistent_dir(self, tmp_path: Path) -> None:
        tool = ListFilesTool(workspace_root=tmp_path)
        result = tool.execute({"path": "nope"})
        assert "error" in result
