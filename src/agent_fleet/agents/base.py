"""Agent configuration model parsed from YAML."""

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for a single agent, loaded from YAML."""

    name: str
    description: str
    capabilities: list[str]
    tools: list[str]
    default_model: str
    system_prompt: str
    max_retries: int = Field(default=2)
    timeout_minutes: int = Field(default=30)
    max_tokens: int = Field(default=100000)
    can_delegate: list[str] = Field(default_factory=list)
