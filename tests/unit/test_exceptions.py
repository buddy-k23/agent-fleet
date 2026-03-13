from agent_fleet.exceptions import (
    AgentFleetError,
    AgentNotFoundError,
    GateFailedError,
    LLMProviderError,
    TaskError,
    WorkflowNotFoundError,
    WorktreeError,
)


def test_base_exception_has_message():
    err = AgentFleetError("something broke")
    assert str(err) == "something broke"
    assert isinstance(err, Exception)


def test_agent_not_found():
    err = AgentNotFoundError("architect")
    assert "architect" in str(err)
    assert isinstance(err, AgentFleetError)


def test_workflow_not_found():
    err = WorkflowNotFoundError("custom-pipeline")
    assert "custom-pipeline" in str(err)
    assert isinstance(err, AgentFleetError)


def test_gate_failed_has_details():
    err = GateFailedError(stage="review", reason="score 60 < 80")
    assert err.stage == "review"
    assert err.reason == "score 60 < 80"
    assert isinstance(err, AgentFleetError)


def test_worktree_error():
    err = WorktreeError("disk full")
    assert "disk full" in str(err)
    assert isinstance(err, AgentFleetError)


def test_task_error_has_task_id():
    err = TaskError(task_id="task-123", reason="timeout")
    assert err.task_id == "task-123"
    assert err.reason == "timeout"
    assert isinstance(err, AgentFleetError)


def test_llm_provider_error():
    err = LLMProviderError("rate limited")
    assert "rate limited" in str(err)
    assert isinstance(err, AgentFleetError)
