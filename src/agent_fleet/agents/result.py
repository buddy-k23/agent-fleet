"""AgentResult — return type from an agent run."""

from pydantic import BaseModel


class AgentResult(BaseModel):
    """Structured result from an agent's ReAct tool loop execution."""

    success: bool
    output: str
    files_changed: list[str]
    tokens_used: int
    iterations: int
    tool_calls: list[dict]
