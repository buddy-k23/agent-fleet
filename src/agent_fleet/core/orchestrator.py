"""LangGraph orchestrator — the core state graph."""

from pathlib import Path
from typing import Literal

import structlog
from langgraph.graph import StateGraph

from agent_fleet.agents.registry import AgentRegistry
from agent_fleet.core.events import log_event
from agent_fleet.core.router import Router
from agent_fleet.core.state import FleetState
from agent_fleet.core.workflow import WorkflowConfig, load_workflow

logger = structlog.get_logger()

# Terminal states that end the graph
_TERMINAL_STATES = frozenset({"completed", "error", "interrupted", "cost_limit"})


def should_continue(state: FleetState) -> Literal["route_next", "__end__"]:
    """Decide whether to continue routing or finish the graph."""
    status = state.get("status", "running")
    if status in _TERMINAL_STATES:
        return "__end__"
    return "route_next"


class FleetOrchestrator:
    """Orchestrator with injected dependencies for workflow execution."""

    def __init__(
        self,
        workflow_path: Path,
        agents_dir: Path,
        repo_path: Path | None = None,
    ) -> None:
        self._workflow = load_workflow(workflow_path)
        self._router = Router(self._workflow)
        self._registry = AgentRegistry(agents_dir)
        self._repo_path = repo_path

    @property
    def workflow(self) -> WorkflowConfig:
        return self._workflow

    def route_next(self, state: FleetState) -> FleetState:
        """Determine the next stage to execute based on DAG dependencies."""
        completed = set(state.get("completed_stages", []))
        log_event(
            state["task_id"],
            "route",
            {"completed": list(completed)},
        )

        ready = self._router.get_next_stages(completed)

        if not ready:
            logger.info("orchestrator_complete", task_id=state["task_id"])
            return {**state, "status": "completed", "current_stage": None}

        # Sequential for PoC — pick first ready stage
        next_stage = ready[0].name
        logger.info(
            "orchestrator_route",
            task_id=state["task_id"],
            next_stage=next_stage,
        )
        return {**state, "current_stage": next_stage}

    def execute_stage(self, state: FleetState) -> FleetState:
        """Execute the current stage's agent. (Stub — wired in #29)"""
        stage = state.get("current_stage")
        log_event(state["task_id"], "execute", {"stage": stage})
        return state

    def evaluate_gate(self, state: FleetState) -> FleetState:
        """Evaluate the gate for the current stage. (Stub — wired in #30)"""
        stage = state.get("current_stage")
        log_event(state["task_id"], "gate", {"stage": stage})
        return state

    def build_graph(self) -> StateGraph:
        """Build and compile the LangGraph state graph."""
        graph = StateGraph(FleetState)

        graph.add_node("route_next", self.route_next)
        graph.add_node("execute_stage", self.execute_stage)
        graph.add_node("evaluate_gate", self.evaluate_gate)

        graph.set_entry_point("route_next")
        graph.add_edge("route_next", "execute_stage")
        graph.add_edge("execute_stage", "evaluate_gate")
        graph.add_conditional_edges("evaluate_gate", should_continue)

        return graph.compile()


# Backward-compatible standalone functions for existing tests
def route_next(state: FleetState) -> FleetState:
    """Stub route_next for backward compatibility."""
    log_event(
        state["task_id"],
        "route",
        {"completed": state.get("completed_stages", [])},
    )
    return state


def execute_stage(state: FleetState) -> FleetState:
    """Stub execute_stage for backward compatibility."""
    stage = state.get("current_stage")
    log_event(state["task_id"], "execute", {"stage": stage})
    return state


def evaluate_gate(state: FleetState) -> FleetState:
    """Stub evaluate_gate for backward compatibility."""
    stage = state.get("current_stage")
    log_event(state["task_id"], "gate", {"stage": stage})
    return state


def build_orchestrator_graph() -> StateGraph:
    """Build orchestrator graph with stub functions (backward compatible)."""
    graph = StateGraph(FleetState)

    graph.add_node("route_next", route_next)
    graph.add_node("execute_stage", execute_stage)
    graph.add_node("evaluate_gate", evaluate_gate)

    graph.set_entry_point("route_next")
    graph.add_edge("route_next", "execute_stage")
    graph.add_edge("execute_stage", "evaluate_gate")
    graph.add_conditional_edges("evaluate_gate", should_continue)

    return graph.compile()
