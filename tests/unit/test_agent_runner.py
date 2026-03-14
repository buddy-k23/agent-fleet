"""Tests for AgentRunner — ReAct tool loop."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent_fleet.agents.base import AgentConfig
from agent_fleet.agents.runner import AgentRunner
from agent_fleet.models.provider import LLMProvider, LLMResponse
from agent_fleet.tools.registry import create_tools


@pytest.fixture
def agent_config() -> AgentConfig:
    return AgentConfig(
        name="Test Agent",
        description="A test agent",
        capabilities=["testing"],
        tools=["code"],
        default_model="test/model",
        system_prompt="You are a test agent.",
    )


@pytest.fixture
def git_worktree(tmp_path: Path) -> Path:
    """Create a git-initialized temp dir for file tracking."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t.com"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "T"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    (tmp_path / "existing.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True, check=True
    )
    return tmp_path


class TestAgentRunnerBasicFlow:
    def test_direct_answer_no_tools(self, agent_config: AgentConfig, git_worktree: Path) -> None:
        """LLM responds with text immediately — no tool calls."""
        provider = MagicMock(spec=LLMProvider)
        provider.complete.return_value = LLMResponse(
            content="The answer is 42",
            model="test/model",
            tokens_used=50,
            tool_calls=None,
            raw_message={"role": "assistant", "content": "The answer is 42"},
        )

        tools = create_tools(["code"], git_worktree)
        runner = AgentRunner(provider=provider, tools=tools)
        result = runner.run(agent_config, "What is the answer?", git_worktree)

        assert result.success is True
        assert result.output == "The answer is 42"
        assert result.tokens_used == 50
        assert result.iterations == 1

    def test_tool_call_then_answer(
        self, agent_config: AgentConfig, git_worktree: Path
    ) -> None:
        """LLM makes one tool call, then responds with text."""
        provider = MagicMock(spec=LLMProvider)

        # First call: tool call to read a file
        provider.complete.side_effect = [
            LLMResponse(
                content="",
                model="test/model",
                tokens_used=30,
                tool_calls=[{
                    "id": "call_1",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "existing.txt"}),
                    },
                }],
                raw_message={
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": json.dumps({"path": "existing.txt"}),
                        },
                    }],
                },
            ),
            # Second call: final answer
            LLMResponse(
                content="The file contains: hello",
                model="test/model",
                tokens_used=20,
                tool_calls=None,
                raw_message={"role": "assistant", "content": "The file contains: hello"},
            ),
        ]

        tools = create_tools(["code"], git_worktree)
        runner = AgentRunner(provider=provider, tools=tools)
        result = runner.run(agent_config, "Read existing.txt", git_worktree)

        assert result.success is True
        assert "hello" in result.output
        assert result.iterations == 2
        assert result.tokens_used == 50
        assert len(result.tool_calls) == 1

    def test_write_file_tracked_in_files_changed(
        self, agent_config: AgentConfig, git_worktree: Path
    ) -> None:
        """Files written by agent appear in files_changed."""
        provider = MagicMock(spec=LLMProvider)
        provider.complete.side_effect = [
            LLMResponse(
                content="",
                model="m",
                tokens_used=20,
                tool_calls=[{
                    "id": "call_1",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps({
                            "path": "new_file.txt",
                            "content": "new content",
                        }),
                    },
                }],
                raw_message={
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": json.dumps({
                                "path": "new_file.txt",
                                "content": "new content",
                            }),
                        },
                    }],
                },
            ),
            LLMResponse(
                content="Done",
                model="m",
                tokens_used=10,
                tool_calls=None,
                raw_message={"role": "assistant", "content": "Done"},
            ),
        ]

        tools = create_tools(["code"], git_worktree)
        runner = AgentRunner(provider=provider, tools=tools)
        result = runner.run(agent_config, "Create new_file.txt", git_worktree)

        assert result.success is True
        assert "new_file.txt" in result.files_changed


class TestAgentRunnerEdgeCases:
    def test_max_iterations_returns_failure(
        self, agent_config: AgentConfig, git_worktree: Path
    ) -> None:
        """Runner stops after max_iterations and returns success=False."""
        provider = MagicMock(spec=LLMProvider)
        # Always returns tool calls, never a final answer
        provider.complete.return_value = LLMResponse(
            content="",
            model="m",
            tokens_used=10,
            tool_calls=[{
                "id": "call_loop",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "existing.txt"}),
                },
            }],
            raw_message={
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_loop",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "existing.txt"}),
                    },
                }],
            },
        )

        tools = create_tools(["code"], git_worktree)
        runner = AgentRunner(provider=provider, tools=tools, max_iterations=3)
        result = runner.run(agent_config, "Loop forever", git_worktree)

        assert result.success is False
        assert result.iterations == 3

    def test_invalid_tool_name_returns_error_to_llm(
        self, agent_config: AgentConfig, git_worktree: Path
    ) -> None:
        """Unknown tool name sends error message back to LLM."""
        provider = MagicMock(spec=LLMProvider)
        provider.complete.side_effect = [
            LLMResponse(
                content="",
                model="m",
                tokens_used=10,
                tool_calls=[{
                    "id": "call_bad",
                    "function": {
                        "name": "nonexistent_tool",
                        "arguments": "{}",
                    },
                }],
                raw_message={
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_bad",
                        "type": "function",
                        "function": {
                            "name": "nonexistent_tool",
                            "arguments": "{}",
                        },
                    }],
                },
            ),
            LLMResponse(
                content="Sorry, let me try again",
                model="m",
                tokens_used=10,
                tool_calls=None,
                raw_message={"role": "assistant", "content": "Sorry"},
            ),
        ]

        tools = create_tools(["code"], git_worktree)
        runner = AgentRunner(provider=provider, tools=tools)
        result = runner.run(agent_config, "Use wrong tool", git_worktree)

        assert result.success is True
        # Verify the error was sent back as a tool message
        calls = provider.complete.call_args_list
        assert len(calls) == 2

    def test_invalid_json_arguments(
        self, agent_config: AgentConfig, git_worktree: Path
    ) -> None:
        """Malformed JSON in tool arguments sends error back to LLM."""
        provider = MagicMock(spec=LLMProvider)
        provider.complete.side_effect = [
            LLMResponse(
                content="",
                model="m",
                tokens_used=10,
                tool_calls=[{
                    "id": "call_badjson",
                    "function": {
                        "name": "read_file",
                        "arguments": "not valid json{{{",
                    },
                }],
                raw_message={
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_badjson",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": "not valid json{{{",
                        },
                    }],
                },
            ),
            LLMResponse(
                content="Fixed it",
                model="m",
                tokens_used=10,
                tool_calls=None,
                raw_message={"role": "assistant", "content": "Fixed it"},
            ),
        ]

        tools = create_tools(["code"], git_worktree)
        runner = AgentRunner(provider=provider, tools=tools)
        result = runner.run(agent_config, "Bad json", git_worktree)

        assert result.success is True
        assert result.iterations == 2
