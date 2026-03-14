"""Tests for LiteLLM provider wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from agent_fleet.exceptions import LLMProviderError
from agent_fleet.models.provider import LLMProvider, LLMResponse


def test_llm_response_model() -> None:
    resp = LLMResponse(
        content="Hello world",
        model="anthropic/claude-sonnet-4-6",
        tokens_used=150,
        cost_usd=0.003,
    )
    assert resp.content == "Hello world"
    assert resp.tokens_used == 150
    assert resp.cost_usd == 0.003


@patch("agent_fleet.models.provider.litellm_completion")
def test_completion_calls_litellm(mock_completion: MagicMock) -> None:
    mock_choice = MagicMock()
    mock_choice.message.content = "Test response"
    mock_result = MagicMock()
    mock_result.choices = [mock_choice]
    mock_result.model = "anthropic/claude-sonnet-4-6"
    mock_result.usage.total_tokens = 200
    mock_completion.return_value = mock_result

    provider = LLMProvider()
    result = provider.complete(
        model="anthropic/claude-sonnet-4-6",
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert result.content == "Test response"
    assert result.tokens_used == 200
    mock_completion.assert_called_once()


@patch("agent_fleet.models.provider.litellm_completion")
def test_completion_tracks_token_usage(mock_completion: MagicMock) -> None:
    mock_choice = MagicMock()
    mock_choice.message.content = "Response"
    mock_result = MagicMock()
    mock_result.choices = [mock_choice]
    mock_result.model = "test-model"
    mock_result.usage.total_tokens = 500
    mock_completion.return_value = mock_result

    provider = LLMProvider()
    provider.complete(model="test-model", messages=[{"role": "user", "content": "Hi"}])
    assert provider.total_tokens_used == 500

    provider.complete(model="test-model", messages=[{"role": "user", "content": "Hi"}])
    assert provider.total_tokens_used == 1000


@patch("agent_fleet.models.provider.litellm_completion")
def test_within_budget_true(mock_completion: MagicMock) -> None:
    mock_choice = MagicMock()
    mock_choice.message.content = "R"
    mock_result = MagicMock()
    mock_result.choices = [mock_choice]
    mock_result.model = "m"
    mock_result.usage.total_tokens = 100
    mock_completion.return_value = mock_result

    provider = LLMProvider()
    provider.complete(model="m", messages=[{"role": "user", "content": "x"}])
    assert provider.within_budget(max_tokens=1000) is True


@patch("agent_fleet.models.provider.litellm_completion")
def test_within_budget_false(mock_completion: MagicMock) -> None:
    mock_choice = MagicMock()
    mock_choice.message.content = "R"
    mock_result = MagicMock()
    mock_result.choices = [mock_choice]
    mock_result.model = "m"
    mock_result.usage.total_tokens = 5000
    mock_completion.return_value = mock_result

    provider = LLMProvider()
    provider.complete(model="m", messages=[{"role": "user", "content": "x"}])
    assert provider.within_budget(max_tokens=1000) is False


@patch("agent_fleet.models.provider.litellm_completion")
def test_completion_failure_raises_llm_provider_error(mock_completion: MagicMock) -> None:
    mock_completion.side_effect = Exception("API rate limited")

    provider = LLMProvider()
    with pytest.raises(LLMProviderError, match="LLM call failed"):
        provider.complete(
            model="anthropic/claude-sonnet-4-6",
            messages=[{"role": "user", "content": "Hi"}],
        )


@patch("agent_fleet.models.provider.litellm_completion")
def test_completion_with_tools(mock_completion: MagicMock) -> None:
    mock_choice = MagicMock()
    mock_choice.message.content = "Tool result"
    mock_result = MagicMock()
    mock_result.choices = [mock_choice]
    mock_result.model = "m"
    mock_result.usage.total_tokens = 300
    mock_completion.return_value = mock_result

    provider = LLMProvider()
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    result = provider.complete(
        model="m",
        messages=[{"role": "user", "content": "Read file"}],
        tools=tools,
    )
    assert result.content == "Tool result"
    call_kwargs = mock_completion.call_args[1]
    assert "tools" in call_kwargs


def test_llm_response_tool_calls_default_none() -> None:
    resp = LLMResponse(content="Hi", model="m", tokens_used=10)
    assert resp.tool_calls is None
    assert resp.raw_message is None


@patch("agent_fleet.models.provider.litellm_completion")
def test_completion_returns_tool_calls(mock_completion: MagicMock) -> None:
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "read_file"
    mock_tool_call.function.arguments = '{"path": "src/main.py"}'

    mock_choice = MagicMock()
    mock_choice.message.content = None
    mock_choice.message.tool_calls = [mock_tool_call]
    mock_choice.message.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{"id": "call_123", "function": {"name": "read_file", "arguments": '{"path": "src/main.py"}'}}],
    }

    mock_result = MagicMock()
    mock_result.choices = [mock_choice]
    mock_result.model = "m"
    mock_result.usage.total_tokens = 100
    mock_completion.return_value = mock_result

    provider = LLMProvider()
    result = provider.complete(model="m", messages=[{"role": "user", "content": "Read"}])
    assert result.content == ""
    assert result.tool_calls is not None
    assert len(result.tool_calls) == 1
    assert result.raw_message is not None


@patch("agent_fleet.models.provider.litellm_completion")
def test_completion_no_tool_calls_returns_none(mock_completion: MagicMock) -> None:
    mock_choice = MagicMock()
    mock_choice.message.content = "Plain text"
    mock_choice.message.tool_calls = None
    mock_choice.message.model_dump.return_value = {"role": "assistant", "content": "Plain text"}

    mock_result = MagicMock()
    mock_result.choices = [mock_choice]
    mock_result.model = "m"
    mock_result.usage.total_tokens = 50
    mock_completion.return_value = mock_result

    provider = LLMProvider()
    result = provider.complete(model="m", messages=[{"role": "user", "content": "Hi"}])
    assert result.content == "Plain text"
    assert result.tool_calls is None
