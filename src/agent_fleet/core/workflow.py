"""Workflow configuration model and loader."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class GateConfig(BaseModel):
    """Configuration for a quality gate checkpoint."""

    type: str  # automated, score, approval, custom
    checks: list[str] = Field(default_factory=list)
    min_score: int | None = None
    scored_by: str = "reviewer"
    on_fail: str = "retry"  # retry, route_to, halt
    route_target: str | None = None
    max_retries: int | None = None


class ReactionConfig(BaseModel):
    """Configuration for an auto-response to an event."""

    action: str
    retries: int = 1


class StageConfig(BaseModel):
    """Configuration for a single pipeline stage."""

    name: str
    agent: str
    model: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    gate: GateConfig = Field(default_factory=lambda: GateConfig(type="automated"))
    reactions: dict[str, ReactionConfig] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_depends_on(cls, data: dict) -> dict:  # type: ignore[type-arg]
        """Normalize depends_on to always be a list."""
        deps = data.get("depends_on")
        if deps is None:
            data["depends_on"] = []
        elif isinstance(deps, str):
            data["depends_on"] = [deps]
        return data


class WorkflowConfig(BaseModel):
    """Configuration for a complete workflow pipeline."""

    name: str
    concurrency: int = 1
    max_cost_usd: float | None = None
    classifier_mode: str = "suggest"  # suggest, override, disabled
    stages: list[StageConfig]

    def get_stage(self, name: str) -> StageConfig:
        """Get a stage by name. Raises ValueError if not found."""
        for stage in self.stages:
            if stage.name == name:
                return stage
        raise ValueError(f"Stage not found: {name}")

    def get_ready_stages(self, completed: set[str]) -> list[StageConfig]:
        """Return stages whose dependencies are all in the completed set."""
        ready: list[StageConfig] = []
        for stage in self.stages:
            if stage.name in completed:
                continue
            if all(dep in completed for dep in stage.depends_on):
                ready.append(stage)
        return ready


def load_workflow(path: Path) -> WorkflowConfig:
    """Load a workflow config from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return WorkflowConfig(**data)
