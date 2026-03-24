"""Factory for building a StatusWriter from Supabase data."""

from agent_fleet.agents.registry import AgentRegistry
from agent_fleet.core.workflow import WorkflowConfig
from agent_fleet.worker.status_writer import StatusWriter


class OrchestratorFactory:
    """Builds a persistence-aware orchestrator from Supabase data."""

    @staticmethod
    def from_supabase(
        workflow_data: dict,
        agent_configs: list[dict],
        task_id: str,
        repos: dict,
    ) -> StatusWriter:
        """Build a StatusWriter from Supabase workflow + agent rows."""
        workflow = WorkflowConfig(**workflow_data)
        registry = AgentRegistry.from_configs(agent_configs)

        return StatusWriter(
            repos=repos,
            task_id=task_id,
            workflow=workflow,
            registry=registry,
        )
