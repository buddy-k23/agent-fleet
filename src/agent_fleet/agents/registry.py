"""Load and validate agent definitions from YAML files."""

from pathlib import Path

import structlog
import yaml

from agent_fleet.agents.base import AgentConfig
from agent_fleet.exceptions import AgentNotFoundError

logger = structlog.get_logger()


class AgentRegistry:
    """Registry of agent configurations loaded from a directory of YAML files."""

    def __init__(self, config_dir: Path) -> None:
        self._agents: dict[str, AgentConfig] = {}
        self._load(config_dir)

    def _load(self, config_dir: Path) -> None:
        if not config_dir.is_dir():
            logger.warning("agent_config_dir_not_found", path=str(config_dir))
            return
        for yaml_file in sorted(config_dir.glob("*.yaml")):
            key = yaml_file.stem
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            self._agents[key] = AgentConfig(**data)
            logger.info("agent_loaded", agent=key)

    def get(self, agent_name: str) -> AgentConfig:
        """Get agent config by name. Raises AgentNotFoundError if not found."""
        if agent_name not in self._agents:
            raise AgentNotFoundError(agent_name)
        return self._agents[agent_name]

    def list_agents(self) -> list[str]:
        """Return all registered agent names."""
        return list(self._agents.keys())

    def has(self, agent_name: str) -> bool:
        """Check if an agent exists in the registry."""
        return agent_name in self._agents
