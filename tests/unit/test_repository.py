"""Tests for repository CRUD operations."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from agent_fleet.store.models import Base
from agent_fleet.store.repository import (
    EventRepository,
    ExecutionRepository,
    GateResultRepository,
    TaskRepository,
)


@pytest.fixture
def db_session() -> Session:  # type: ignore[misc]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestTaskRepository:
    def test_create_task(self, db_session: Session) -> None:
        repo = TaskRepository(db_session)
        task = repo.create(
            task_id="task-001",
            repo_path="/path/to/repo",
            description="Test task",
            workflow="default",
        )
        assert task.id == "task-001"
        assert task.status == "queued"
        assert task.created_at is not None

    def test_get_task(self, db_session: Session) -> None:
        repo = TaskRepository(db_session)
        repo.create(task_id="task-002", repo_path="/repo", description="Test", workflow="default")
        task = repo.get("task-002")
        assert task is not None
        assert task.description == "Test"

    def test_get_nonexistent_returns_none(self, db_session: Session) -> None:
        repo = TaskRepository(db_session)
        assert repo.get("nope") is None

    def test_update_status(self, db_session: Session) -> None:
        repo = TaskRepository(db_session)
        repo.create(task_id="task-003", repo_path="/repo", description="Test", workflow="default")
        repo.update_status("task-003", "running")
        task = repo.get("task-003")
        assert task is not None
        assert task.status == "running"

    def test_list_by_status(self, db_session: Session) -> None:
        repo = TaskRepository(db_session)
        repo.create(task_id="t1", repo_path="/r", description="A", workflow="default")
        repo.create(task_id="t2", repo_path="/r", description="B", workflow="default")
        repo.update_status("t1", "running")
        queued = repo.list_by_status("queued")
        assert len(queued) == 1
        assert queued[0].id == "t2"

    def test_list_all(self, db_session: Session) -> None:
        repo = TaskRepository(db_session)
        repo.create(task_id="t-a", repo_path="/r", description="A", workflow="default")
        repo.create(task_id="t-b", repo_path="/r", description="B", workflow="default")
        all_tasks = repo.list_all()
        assert len(all_tasks) == 2


class TestExecutionRepository:
    def test_create_execution(self, db_session: Session) -> None:
        task_repo = TaskRepository(db_session)
        task_repo.create(task_id="task-ex1", repo_path="/r", description="T", workflow="default")
        exec_repo = ExecutionRepository(db_session)
        execution = exec_repo.create(
            task_id="task-ex1",
            stage="plan",
            agent="architect",
            model="anthropic/claude-opus-4-6",
            worktree_path="/tmp/wt",
        )
        assert execution.id is not None
        assert execution.agent == "architect"
        assert execution.status == "running"

    def test_get_execution(self, db_session: Session) -> None:
        task_repo = TaskRepository(db_session)
        task_repo.create(task_id="task-ex2", repo_path="/r", description="T", workflow="default")
        exec_repo = ExecutionRepository(db_session)
        created = exec_repo.create(
            task_id="task-ex2", stage="plan", agent="architect", model="m"
        )
        loaded = exec_repo.get(created.id)
        assert loaded is not None
        assert loaded.stage == "plan"

    def test_update_status(self, db_session: Session) -> None:
        task_repo = TaskRepository(db_session)
        task_repo.create(task_id="task-ex3", repo_path="/r", description="T", workflow="default")
        exec_repo = ExecutionRepository(db_session)
        created = exec_repo.create(
            task_id="task-ex3", stage="plan", agent="architect", model="m"
        )
        exec_repo.update_status(created.id, "completed", summary="All done")
        loaded = exec_repo.get(created.id)
        assert loaded is not None
        assert loaded.status == "completed"
        assert loaded.summary == "All done"


class TestGateResultRepository:
    def test_create_gate_result(self, db_session: Session) -> None:
        task_repo = TaskRepository(db_session)
        task_repo.create(task_id="task-gr1", repo_path="/r", description="T", workflow="default")
        exec_repo = ExecutionRepository(db_session)
        execution = exec_repo.create(
            task_id="task-gr1", stage="review", agent="reviewer", model="m"
        )
        gate_repo = GateResultRepository(db_session)
        result = gate_repo.create(
            execution_id=execution.id,
            gate_type="score",
            passed=False,
            details={"score": 60, "min_score": 80},
        )
        assert result.id is not None
        assert result.passed is False
        assert result.details["score"] == 60


class TestEventRepository:
    def test_append_event(self, db_session: Session) -> None:
        task_repo = TaskRepository(db_session)
        task_repo.create(task_id="task-e1", repo_path="/r", description="T", workflow="default")
        event_repo = EventRepository(db_session)
        event = event_repo.append(
            task_id="task-e1",
            event_type="action",
            payload={"tool": "shell", "command": "pytest"},
        )
        assert event.id is not None
        assert event.event_type == "action"
        assert event.timestamp is not None

    def test_list_events_for_task(self, db_session: Session) -> None:
        task_repo = TaskRepository(db_session)
        task_repo.create(task_id="task-e2", repo_path="/r", description="T", workflow="default")
        event_repo = EventRepository(db_session)
        event_repo.append(task_id="task-e2", event_type="action", payload={"a": 1})
        event_repo.append(task_id="task-e2", event_type="observation", payload={"b": 2})
        events = event_repo.list_for_task("task-e2")
        assert len(events) == 2
        assert events[0].event_type == "action"
        assert events[1].event_type == "observation"

    def test_events_ordered_by_timestamp(self, db_session: Session) -> None:
        task_repo = TaskRepository(db_session)
        task_repo.create(task_id="task-e3", repo_path="/r", description="T", workflow="default")
        event_repo = EventRepository(db_session)
        event_repo.append(task_id="task-e3", event_type="first", payload={})
        event_repo.append(task_id="task-e3", event_type="second", payload={})
        event_repo.append(task_id="task-e3", event_type="third", payload={})
        events = event_repo.list_for_task("task-e3")
        assert [e.event_type for e in events] == ["first", "second", "third"]

    def test_append_event_with_execution_id(self, db_session: Session) -> None:
        task_repo = TaskRepository(db_session)
        task_repo.create(task_id="task-e4", repo_path="/r", description="T", workflow="default")
        exec_repo = ExecutionRepository(db_session)
        execution = exec_repo.create(
            task_id="task-e4", stage="plan", agent="architect", model="m"
        )
        event_repo = EventRepository(db_session)
        event = event_repo.append(
            task_id="task-e4",
            event_type="action",
            payload={"tool": "code"},
            execution_id=execution.id,
        )
        assert event.execution_id == execution.id
