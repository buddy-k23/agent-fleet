"""CRUD operations for Agent Fleet state store."""

import structlog
from sqlalchemy.orm import Session

from agent_fleet.store.models import (
    EventRecord,
    ExecutionRecord,
    GateResultRecord,
    TaskRecord,
)

logger = structlog.get_logger()


class TaskRepository:
    """CRUD operations for task records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, task_id: str, repo_path: str, description: str, workflow: str
    ) -> TaskRecord:
        task = TaskRecord(
            id=task_id, repo=repo_path, description=description, workflow=workflow
        )
        self._session.add(task)
        self._session.commit()
        self._session.refresh(task)
        logger.info("task_created", task_id=task_id, workflow=workflow)
        return task

    def get(self, task_id: str) -> TaskRecord | None:
        return self._session.get(TaskRecord, task_id)

    def update_status(self, task_id: str, status: str) -> None:
        task = self.get(task_id)
        if task:
            task.status = status
            self._session.commit()
            logger.info("task_status_updated", task_id=task_id, status=status)

    def list_by_status(self, status: str) -> list[TaskRecord]:
        return list(
            self._session.query(TaskRecord).filter(TaskRecord.status == status).all()
        )

    def list_all(self) -> list[TaskRecord]:
        return list(
            self._session.query(TaskRecord).order_by(TaskRecord.created_at.desc()).all()
        )


class ExecutionRepository:
    """CRUD operations for execution records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        task_id: str,
        stage: str,
        agent: str,
        model: str,
        worktree_path: str | None = None,
    ) -> ExecutionRecord:
        execution = ExecutionRecord(
            task_id=task_id,
            stage=stage,
            agent=agent,
            model=model,
            worktree_path=worktree_path,
        )
        self._session.add(execution)
        self._session.commit()
        self._session.refresh(execution)
        logger.info(
            "execution_created", task_id=task_id, stage=stage, agent=agent
        )
        return execution

    def get(self, execution_id: int) -> ExecutionRecord | None:
        return self._session.get(ExecutionRecord, execution_id)

    def update_status(
        self, execution_id: int, status: str, summary: str | None = None
    ) -> None:
        execution = self.get(execution_id)
        if execution:
            execution.status = status
            if summary:
                execution.summary = summary
            self._session.commit()
            logger.info(
                "execution_status_updated",
                execution_id=execution_id,
                status=status,
            )


class GateResultRepository:
    """CRUD operations for gate result records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        execution_id: int,
        gate_type: str,
        passed: bool,
        details: dict | None = None,
    ) -> GateResultRecord:
        result = GateResultRecord(
            execution_id=execution_id,
            gate_type=gate_type,
            passed=passed,
            details=details,
        )
        self._session.add(result)
        self._session.commit()
        self._session.refresh(result)
        logger.info(
            "gate_result_created",
            execution_id=execution_id,
            gate_type=gate_type,
            passed=passed,
        )
        return result


class EventRepository:
    """Append-only event log operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        task_id: str,
        event_type: str,
        payload: dict,
        execution_id: int | None = None,
    ) -> EventRecord:
        event = EventRecord(
            task_id=task_id,
            execution_id=execution_id,
            event_type=event_type,
            payload=payload,
        )
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return event

    def list_for_task(self, task_id: str) -> list[EventRecord]:
        return list(
            self._session.query(EventRecord)
            .filter(EventRecord.task_id == task_id)
            .order_by(EventRecord.timestamp)
            .all()
        )
