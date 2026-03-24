"""Tests for agent registry YAML loader."""

from pathlib import Path

import pytest

from agent_fleet.agents.registry import AgentRegistry
from agent_fleet.exceptions import AgentNotFoundError

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "agents"


def test_load_agents_from_directory() -> None:
    registry = AgentRegistry(FIXTURES_DIR)
    agents = registry.list_agents()
    assert len(agents) >= 1
    assert "test-agent" in agents


def test_get_agent_config() -> None:
    registry = AgentRegistry(FIXTURES_DIR)
    config = registry.get("test-agent")
    assert config.name == "Test Agent"
    assert config.default_model == "anthropic/claude-sonnet-4-6"
    assert "code" in config.tools
    assert config.max_retries == 1


def test_get_nonexistent_raises() -> None:
    registry = AgentRegistry(FIXTURES_DIR)
    with pytest.raises(AgentNotFoundError):
        registry.get("nonexistent-agent")


def test_agent_key_is_filename_stem() -> None:
    registry = AgentRegistry(FIXTURES_DIR)
    assert "test-agent" in registry.list_agents()


def test_has_agent() -> None:
    registry = AgentRegistry(FIXTURES_DIR)
    assert registry.has("test-agent") is True
    assert registry.has("nonexistent") is False


def test_empty_directory() -> None:
    registry = AgentRegistry(Path("/nonexistent/path"))
    assert registry.list_agents() == []


def test_from_configs_builds_registry_from_dicts() -> None:
    """Build AgentRegistry from list of config dicts (Supabase rows)."""
    configs = [
        {
            "name": "Architect",
            "description": "Designs solutions",
            "capabilities": ["code_analysis"],
            "tools": ["code"],
            "default_model": "anthropic/claude-opus-4-6",
            "system_prompt": "You are an architect.",
        },
        {
            "name": "Tester",
            "description": "Writes tests",
            "capabilities": ["testing"],
            "tools": ["code", "shell"],
            "default_model": "anthropic/claude-sonnet-4-6",
            "system_prompt": "You are a tester.",
        },
    ]
    registry = AgentRegistry.from_configs(configs)
    assert registry.has("Architect")
    assert registry.has("Tester")
    assert registry.get("Architect").default_model == "anthropic/claude-opus-4-6"
    assert registry.list_agents() == ["Architect", "Tester"]
