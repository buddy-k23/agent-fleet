"""Custom exception hierarchy for Agent Fleet."""


class AgentFleetError(Exception):
    """Base exception for all Agent Fleet errors."""


class AgentNotFoundError(AgentFleetError):
    """Raised when an agent definition is not found in the registry."""

    def __init__(self, agent_name: str) -> None:
        super().__init__(f"Agent not found: {agent_name}")
        self.agent_name = agent_name


class WorkflowNotFoundError(AgentFleetError):
    """Raised when a workflow config is not found."""

    def __init__(self, workflow_name: str) -> None:
        super().__init__(f"Workflow not found: {workflow_name}")
        self.workflow_name = workflow_name


class GateFailedError(AgentFleetError):
    """Raised when a quality gate fails after exhausting retries."""

    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(f"Gate failed at stage '{stage}': {reason}")
        self.stage = stage
        self.reason = reason


class WorktreeError(AgentFleetError):
    """Raised when git worktree operations fail."""


class TaskError(AgentFleetError):
    """Raised for task-level failures."""

    def __init__(self, task_id: str, reason: str) -> None:
        super().__init__(f"Task {task_id} failed: {reason}")
        self.task_id = task_id
        self.reason = reason


class LLMProviderError(AgentFleetError):
    """Raised when an LLM provider call fails after retries."""
