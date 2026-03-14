"""Tests for BaseTool abstract interface."""

import pytest

from agent_fleet.tools.base import BaseTool


def test_base_tool_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseTool()  # type: ignore[abstract]


def test_base_tool_validate_path_within_workspace(tmp_path) -> None:  # type: ignore[no-untyped-def]
    class DummyTool(BaseTool):
        @property
        def name(self) -> str:
            return "dummy"

        @property
        def description(self) -> str:
            return "A dummy tool"

        def execute(self, input: dict) -> dict:  # type: ignore[type-arg]
            return {}

        def schema(self) -> dict:  # type: ignore[type-arg]
            return {}

    tool = DummyTool()
    result = tool._validate_path(tmp_path, "some/file.txt")
    assert result is not None
    assert str(result).startswith(str(tmp_path))


def test_base_tool_validate_path_blocks_outside(tmp_path) -> None:  # type: ignore[no-untyped-def]
    class DummyTool(BaseTool):
        @property
        def name(self) -> str:
            return "dummy"

        @property
        def description(self) -> str:
            return "A dummy tool"

        def execute(self, input: dict) -> dict:  # type: ignore[type-arg]
            return {}

        def schema(self) -> dict:  # type: ignore[type-arg]
            return {}

    tool = DummyTool()
    result = tool._validate_path(tmp_path, "/etc/passwd")
    assert result is None


def test_base_tool_validate_path_blocks_traversal(tmp_path) -> None:  # type: ignore[no-untyped-def]
    class DummyTool(BaseTool):
        @property
        def name(self) -> str:
            return "dummy"

        @property
        def description(self) -> str:
            return "A dummy tool"

        def execute(self, input: dict) -> dict:  # type: ignore[type-arg]
            return {}

        def schema(self) -> dict:  # type: ignore[type-arg]
            return {}

    tool = DummyTool()
    result = tool._validate_path(tmp_path, "../../etc/passwd")
    assert result is None
