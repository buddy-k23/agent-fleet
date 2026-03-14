"""Tests for SQLAlchemy ORM models."""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from agent_fleet.store.models import (
    Base,
    EventRecord,
    ExecutionRecord,
    GateResultRecord,
    TaskRecord,
)


def test_all_tables_created() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "tasks" in tables
    assert "executions" in tables
    assert "gate_results" in tables
    assert "events" in tables


def test_task_record_fields() -> None:
    task = TaskRecord(
        id="task-001",
        repo="/path/to/repo",
        description="Implement feature X",
        status="queued",
        workflow="default",
    )
    assert task.id == "task-001"
    assert task.status == "queued"
    assert task.repo == "/path/to/repo"
    assert task.workflow == "default"


def test_execution_record_fields() -> None:
    execution = ExecutionRecord(
        task_id="task-001",
        stage="plan",
        agent="architect",
        model="anthropic/claude-opus-4-6",
        worktree_path="/tmp/worktree",
    )
    assert execution.agent == "architect"
    assert execution.task_id == "task-001"
    assert execution.stage == "plan"
    assert execution.model == "anthropic/claude-opus-4-6"


def test_gate_result_record_fields() -> None:
    result = GateResultRecord(
        execution_id=1,
        gate_type="score",
        passed=False,
        details={"score": 60, "min_score": 80},
    )
    assert result.gate_type == "score"
    assert result.passed is False
    assert result.details["score"] == 60


def test_event_record_fields() -> None:
    event = EventRecord(
        task_id="task-001",
        execution_id=1,
        event_type="action",
        payload={"tool": "code", "action": "read_file"},
    )
    assert event.event_type == "action"
    assert event.payload["tool"] == "code"


def test_task_record_persists_to_db() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        task = TaskRecord(
            id="task-persist",
            repo="/repo",
            description="Test persistence",
            status="queued",
            workflow="default",
        )
        session.add(task)
        session.commit()

        loaded = session.get(TaskRecord, "task-persist")
        assert loaded is not None
        assert loaded.description == "Test persistence"
        assert loaded.created_at is not None


def test_execution_record_persists_with_fk() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        task = TaskRecord(
            id="task-fk",
            repo="/repo",
            description="FK test",
            status="queued",
            workflow="default",
        )
        session.add(task)
        session.commit()

        execution = ExecutionRecord(
            task_id="task-fk",
            stage="plan",
            agent="architect",
            model="anthropic/claude-opus-4-6",
        )
        session.add(execution)
        session.commit()

        loaded = session.query(ExecutionRecord).filter_by(task_id="task-fk").first()
        assert loaded is not None
        assert loaded.agent == "architect"
        assert loaded.started_at is not None
