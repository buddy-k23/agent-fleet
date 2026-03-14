"""DAG-based stage routing for workflow execution."""

from agent_fleet.core.workflow import StageConfig, WorkflowConfig


class Router:
    """Routes tasks through workflow stages based on DAG dependencies."""

    def __init__(self, workflow: WorkflowConfig) -> None:
        self._workflow = workflow

    def get_next_stages(self, completed: set[str]) -> list[StageConfig]:
        """Return stages ready to execute (all deps met, not yet completed)."""
        return self._workflow.get_ready_stages(completed)

    def get_route_back_target(self, stage_name: str) -> str | None:
        """Get the route_to target for a failed stage's gate."""
        stage = self._workflow.get_stage(stage_name)
        if stage.gate.on_fail == "route_to":
            return stage.gate.route_target
        return None

    def is_complete(self, completed: set[str]) -> bool:
        """Check if all stages are completed."""
        all_stage_names = {s.name for s in self._workflow.stages}
        return all_stage_names <= completed
