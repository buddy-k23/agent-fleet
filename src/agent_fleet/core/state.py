"""LangGraph state schema for the orchestrator."""

from typing import TypedDict


class FleetState(TypedDict, total=False):
    """State carried through the orchestrator graph.

    All fields are optional (total=False) so the graph can be
    initialized with minimal data and populated incrementally.
    """

    # Task identity
    task_id: str
    repo: str
    description: str
    workflow_name: str

    # Progress
    status: str  # queued, running, completed, error, interrupted, cost_limit
    current_stage: str | None
    completed_stages: list[str]
    retry_counts: dict[str, int]  # stage_name -> retry count

    # Agent outputs
    stage_outputs: dict[str, dict]  # stage_name -> agent output
    stage_errors: dict[str, str]  # stage_name -> error message

    # Budget tracking
    total_tokens: int
    total_cost_usd: float

    # Result
    pr_url: str | None
    error_message: str | None
