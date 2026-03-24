"""StatusWriter — wraps FleetOrchestrator with Supabase persistence.

Subclasses FleetOrchestrator and overrides route_next, execute_stage,
and evaluate_gate to write status updates to Supabase before/after
calling the parent implementation. Keeps orchestrator.py pure.
"""

import structlog

from agent_fleet.core.orchestrator import FleetOrchestrator
from agent_fleet.core.state import FleetState

logger = structlog.get_logger()


class StatusWriter(FleetOrchestrator):
    """Orchestrator subclass that persists state to Supabase."""

    def __init__(self, repos: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._repos = repos
        self._current_execution_id: str | None = None

    def route_next(self, state: FleetState) -> FleetState:
        """Route next stage, checking for cancellation first."""
        task_id = state.get("task_id", self._task_id)

        # Check cancellation
        task = self._repos["tasks"].get(task_id)
        if task and task.get("status") == "cancelled":
            logger.info("task_cancelled", task_id=task_id)
            self._repos["events"].append(task_id, "cancelled", {"reason": "User cancelled"})
            return {**state, "status": "interrupted"}

        result = super().route_next(state)

        # Write current stage to Supabase
        current_stage = result.get("current_stage")
        self._repos["tasks"].update_status(task_id, "running", current_stage=current_stage)
        self._repos["events"].append(
            task_id,
            "route",
            {"current_stage": current_stage, "pending_stages": result.get("pending_stages", [])},
        )

        return result

    def execute_stage(self, state: FleetState) -> FleetState:
        """Execute stage with Supabase execution tracking."""
        task_id = state.get("task_id", self._task_id)
        stage_name = state.get("current_stage", "unknown")

        # Look up agent for this stage
        stage_config = self._workflow.get_stage(stage_name)
        agent_name = stage_config.agent if stage_config else "unknown"
        model = stage_config.model or "default" if stage_config else "default"

        # Create execution record
        execution = self._repos["executions"].create(
            task_id=task_id,
            stage=stage_name,
            agent=agent_name,
            model=model,
        )
        self._current_execution_id = execution["id"]

        self._repos["events"].append(
            task_id, "execute_start", {"stage": stage_name, "agent": agent_name}
        )

        try:
            result = super().execute_stage(state)

            # Update execution with results — tolerate Supabase write failures so
            # a transient persistence error never crashes the pipeline itself.
            stage_output = result.get("stage_outputs", {}).get(stage_name, {})
            try:
                self._repos["executions"].update_status(
                    self._current_execution_id,
                    status="completed",
                    summary=stage_output.get("output", "")[:500],
                    tokens_used=result.get("total_tokens", 0),
                    files_changed=stage_output.get("files_changed", []),
                )
            except Exception as write_err:
                logger.warning(
                    "execution_status_write_failed",
                    task_id=task_id,
                    stage=stage_name,
                    error=str(write_err),
                )
            try:
                self._repos["events"].append(
                    task_id,
                    "execute_complete",
                    {"stage": stage_name, "tokens": result.get("total_tokens", 0)},
                )
            except Exception:
                pass
            return result

        except Exception as e:
            logger.error("stage_execution_failed", task_id=task_id, stage=stage_name, error=str(e))
            try:
                self._repos["executions"].update_status(
                    self._current_execution_id,
                    status="error",
                    summary=str(e)[:500],
                )
            except Exception as write_err:
                logger.warning(
                    "execution_error_status_write_failed",
                    task_id=task_id,
                    stage=stage_name,
                    error=str(write_err),
                )
            try:
                self._repos["events"].append(
                    task_id, "execute_error", {"stage": stage_name, "error": str(e)}
                )
            except Exception:
                pass
            return {**state, "status": "error", "error_message": str(e)}

    def evaluate_gate(self, state: FleetState) -> FleetState:
        """Evaluate gate with Supabase result tracking."""
        task_id = state.get("task_id", self._task_id)
        stage_name = state.get("current_stage", "unknown")

        result = super().evaluate_gate(state)

        # Determine if gate passed by checking if stage moved to completed
        completed_before = set(state.get("completed_stages", []))
        completed_after = set(result.get("completed_stages", []))
        passed = stage_name in completed_after and stage_name not in completed_before

        stage_config = self._workflow.get_stage(stage_name)
        gate_type = stage_config.gate.type if stage_config and stage_config.gate else "none"

        self._repos["gate_results"].create(
            execution_id=self._current_execution_id or "unknown",
            gate_type=gate_type,
            passed=passed,
        )
        self._repos["events"].append(
            task_id,
            "gate_evaluated",
            {"stage": stage_name, "gate_type": gate_type, "passed": passed},
        )

        return result
