"""Tests for AgentResult Pydantic model."""

from agent_fleet.agents.result import AgentResult


def test_agent_result_success() -> None:
    result = AgentResult(
        success=True,
        output="Added multiply function",
        files_changed=["src/calculator.py", "tests/test_calculator.py"],
        tokens_used=1500,
        iterations=3,
        tool_calls=[{"tool": "read_file", "args": {"path": "src/calculator.py"}}],
    )
    assert result.success is True
    assert len(result.files_changed) == 2
    assert result.iterations == 3


def test_agent_result_failure() -> None:
    result = AgentResult(
        success=False,
        output="Max iterations reached",
        files_changed=[],
        tokens_used=5000,
        iterations=20,
        tool_calls=[],
    )
    assert result.success is False
    assert result.iterations == 20


def test_agent_result_model_dump() -> None:
    result = AgentResult(
        success=True,
        output="Done",
        files_changed=["a.py"],
        tokens_used=100,
        iterations=1,
        tool_calls=[],
    )
    data = result.model_dump()
    assert data["success"] is True
    assert data["output"] == "Done"
    assert data["files_changed"] == ["a.py"]
    assert isinstance(data, dict)


def test_agent_result_defaults() -> None:
    result = AgentResult(
        success=True,
        output="Done",
        files_changed=[],
        tokens_used=0,
        iterations=0,
        tool_calls=[],
    )
    assert result.tool_calls == []
    assert result.files_changed == []
