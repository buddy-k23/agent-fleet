"""Tests for AgentConfig Pydantic model."""

import pytest

from agent_fleet.agents.base import AgentConfig


def test_parse_minimal_config() -> None:
    config = AgentConfig(
        name="Architect",
        description="Designs solutions",
        capabilities=["code_analysis"],
        tools=["code"],
        default_model="anthropic/claude-opus-4-6",
        system_prompt="You are an architect.",
    )
    assert config.name == "Architect"
    assert config.max_retries == 2
    assert config.timeout_minutes == 30
    assert config.max_tokens == 100000
    assert config.can_delegate == []


def test_parse_full_config() -> None:
    config = AgentConfig(
        name="Architect",
        description="Designs solutions",
        capabilities=["code_analysis", "task_decomposition"],
        tools=["code", "search"],
        default_model="anthropic/claude-opus-4-6",
        system_prompt="You are an architect.",
        max_retries=3,
        timeout_minutes=60,
        max_tokens=200000,
        can_delegate=["backend-dev", "frontend-dev"],
    )
    assert config.max_retries == 3
    assert config.timeout_minutes == 60
    assert config.max_tokens == 200000
    assert config.can_delegate == ["backend-dev", "frontend-dev"]


def test_invalid_config_missing_required() -> None:
    with pytest.raises(Exception):
        AgentConfig(name="Bad")  # type: ignore[call-arg]


def test_capabilities_is_list() -> None:
    config = AgentConfig(
        name="Test",
        description="Test agent",
        capabilities=["a", "b", "c"],
        tools=["code"],
        default_model="test/model",
        system_prompt="Test",
    )
    assert len(config.capabilities) == 3


def test_tools_is_list() -> None:
    config = AgentConfig(
        name="Test",
        description="Test agent",
        capabilities=["testing"],
        tools=["code", "shell", "browser"],
        default_model="test/model",
        system_prompt="Test",
    )
    assert "shell" in config.tools
    assert len(config.tools) == 3
