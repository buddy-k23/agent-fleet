"""LangGraph orchestrator — the core state graph."""

from typing import Literal

import structlog
from langgraph.graph import StateGraph

from agent_fleet.core.events import log_event
from agent_fleet.core.state import FleetState

logger = structlog.get_logger()

# Terminal states that end the graph
_TERMINAL_STATES = frozenset({"completed", "error", "interrupted", "cost_limit"})


def route_next(state: FleetState) -> FleetState:
    """Determine the next stage(s) to execute."""
    log_event(
        state["task_id"],
        "route",
        {"completed": state.get("completed_stages", [])},
    )
    return state


def execute_stage(state: FleetState) -> FleetState:
    """Execute the current stage's agent."""
    stage = state.get("current_stage")
    log_event(state["task_id"], "execute", {"stage": stage})
    return state


def evaluate_gate(state: FleetState) -> FleetState:
    """Evaluate the gate for the current stage."""
    stage = state.get("current_stage")
    log_event(state["task_id"], "gate", {"stage": stage})
    return state


def should_continue(state: FleetState) -> Literal["route_next", "__end__"]:
    """Decide whether to continue routing or finish the graph."""
    status = state.get("status", "running")
    if status in _TERMINAL_STATES:
        return "__end__"
    return "route_next"


def build_orchestrator_graph() -> StateGraph:
    """Build and compile the LangGraph state graph for task orchestration.

    Graph cycle: route_next → execute_stage → evaluate_gate → (continue or end)
    """
    graph = StateGraph(FleetState)

    graph.add_node("route_next", route_next)
    graph.add_node("execute_stage", execute_stage)
    graph.add_node("evaluate_gate", evaluate_gate)

    graph.set_entry_point("route_next")
    graph.add_edge("route_next", "execute_stage")
    graph.add_edge("execute_stage", "evaluate_gate")
    graph.add_conditional_edges("evaluate_gate", should_continue)

    return graph.compile()
