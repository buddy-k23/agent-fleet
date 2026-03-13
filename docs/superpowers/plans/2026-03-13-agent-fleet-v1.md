# Agent Fleet v1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working agent fleet that takes a task + repo, orchestrates specialized agents through quality gates, and produces a PR.

**Architecture:** Bottom-up build — state store → config loaders → LLM provider → tools → workspace → orchestrator → API → CLI. Each layer is testable independently before wiring together.

**Tech Stack:** Python 3.12+, LangGraph, LiteLLM, FastAPI, Typer, SQLAlchemy + Alembic, structlog, pytest, ruff, mypy

**Spec:** `docs/superpowers/specs/2026-03-13-agent-fleet-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Dependencies, scripts, tool config |
| `CLAUDE.md` | Mandatory rules for AI assistants |
| `.env.example` | API key template |
| `src/agent_fleet/__init__.py` | Package init, version |
| `src/agent_fleet/main.py` | FastAPI app factory |
| `src/agent_fleet/exceptions.py` | Custom exception hierarchy |
| `src/agent_fleet/store/database.py` | SQLAlchemy engine + session factory |
| `src/agent_fleet/store/models.py` | ORM table definitions (Task, Execution, GateResult, AgentOutput, Event) |
| `src/agent_fleet/store/repository.py` | CRUD operations for all tables |
| `src/agent_fleet/agents/base.py` | AgentConfig Pydantic model (parsed from YAML) |
| `src/agent_fleet/agents/registry.py` | Load + validate agent YAMLs |
| `src/agent_fleet/agents/runner.py` | Execute agent: LLM + tools + worktree |
| `src/agent_fleet/core/state.py` | LangGraph state schema |
| `src/agent_fleet/core/gates.py` | Gate evaluation (automated, score, approval, custom) |
| `src/agent_fleet/core/router.py` | DAG-based stage resolution |
| `src/agent_fleet/core/events.py` | Event logging helpers |
| `src/agent_fleet/core/orchestrator.py` | LangGraph StateGraph definition |
| `src/agent_fleet/models/provider.py` | LiteLLM wrapper (completion, token tracking) |
| `src/agent_fleet/models/config.py` | Model registry, env-based API key resolution |
| `src/agent_fleet/tools/base.py` | BaseTool abstract class |
| `src/agent_fleet/tools/code.py` | File read/write, grep, code search |
| `src/agent_fleet/tools/shell.py` | Sandboxed command execution |
| `src/agent_fleet/workspace/worktree.py` | Git worktree create/merge/cleanup |
| `src/agent_fleet/workspace/git.py` | Branch, commit, PR operations |
| `src/agent_fleet/api/schemas.py` | Pydantic request/response DTOs |
| `src/agent_fleet/api/routes/tasks.py` | Task CRUD + submission |
| `src/agent_fleet/api/routes/agents.py` | Agent registry endpoints |
| `src/agent_fleet/api/routes/workflows.py` | Workflow config endpoints |
| `cli/main.py` | Typer CLI commands |
| `config/agents/*.yaml` | 6 built-in agent definitions |
| `config/workflows/default.yaml` | Default pipeline |
| `alembic/` | Database migrations |

---

## Chunk 1: Project Scaffolding

### Task 1: Initialize Python project

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/agent_fleet/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "agent-fleet"
version = "0.1.0"
description = "Multi-model AI agent orchestration platform"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "litellm>=1.55.0",
    "langgraph>=0.4.0",
    "langchain-core>=0.3.0",
    "typer>=0.15.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "structlog>=24.4.0",
    "pyyaml>=6.0",
    "gitpython>=3.1.0",
    "httpx>=0.28.0",
    "aiosqlite>=0.20.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "types-PyYAML>=6.0",
]
browser = [
    "playwright>=1.49.0",
]

[project.scripts]
fleet = "cli.main:app"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true

[tool.coverage.run]
source = ["src/agent_fleet"]

[tool.coverage.report]
fail_under = 80

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src", "."]
```

- [ ] **Step 2: Create .env.example**

```bash
# LLM API Keys (set the ones you need)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=

# Local model endpoints (optional)
OLLAMA_API_BASE=http://localhost:11434

# Database (default: SQLite in project dir)
DATABASE_URL=sqlite+aiosqlite:///./agent_fleet.db

# Concurrency
FLEET_MAX_CONCURRENT_TASKS=5
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.env
*.db
.mypy_cache/
.pytest_cache/
.ruff_cache/
htmlcov/
.coverage
```

- [ ] **Step 4: Create package init**

```python
# src/agent_fleet/__init__.py
"""Agent Fleet — Multi-model AI agent orchestration platform."""

__version__ = "0.1.0"
```

- [ ] **Step 5: Install and verify**

Run: `cd /Users/buddy/claude-code/agent-fleet && pip install -e ".[dev]"`
Expected: Successful install, `fleet --help` will fail (CLI not yet created)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .env.example .gitignore src/
git commit -m "feat(scaffold): initialize Python project with dependencies"
```

---

### Task 2: Create CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Write CLAUDE.md**

Use the CLAUDE.md content from the design spec Section 4 (already agreed upon during brainstorming). Copy the full content from the brainstorming conversation.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md with mandatory project rules"
```

---

### Task 3: Create exceptions module

**Files:**
- Create: `src/agent_fleet/exceptions.py`
- Create: `tests/unit/test_exceptions.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_exceptions.py
from agent_fleet.exceptions import (
    AgentFleetError,
    AgentNotFoundError,
    WorkflowNotFoundError,
    GateFailedError,
    WorktreeError,
    TaskError,
    LLMProviderError,
)


def test_base_exception_has_message():
    err = AgentFleetError("something broke")
    assert str(err) == "something broke"
    assert isinstance(err, Exception)


def test_agent_not_found():
    err = AgentNotFoundError("architect")
    assert "architect" in str(err)
    assert isinstance(err, AgentFleetError)


def test_gate_failed_has_details():
    err = GateFailedError(stage="review", reason="score 60 < 80")
    assert err.stage == "review"
    assert err.reason == "score 60 < 80"
    assert isinstance(err, AgentFleetError)


def test_task_error_has_task_id():
    err = TaskError(task_id="task-123", reason="timeout")
    assert err.task_id == "task-123"
    assert isinstance(err, AgentFleetError)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_exceptions.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement exceptions**

```python
# src/agent_fleet/exceptions.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_exceptions.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/agent_fleet/exceptions.py tests/unit/test_exceptions.py
git commit -m "feat(core): add custom exception hierarchy"
```

---

## Chunk 2: State Store

### Task 4: SQLAlchemy models

**Files:**
- Create: `src/agent_fleet/store/__init__.py`
- Create: `src/agent_fleet/store/database.py`
- Create: `src/agent_fleet/store/models.py`
- Create: `tests/unit/test_store_models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_store_models.py
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from agent_fleet.store.models import Base, TaskRecord, ExecutionRecord, GateResultRecord, EventRecord


def test_all_tables_created():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "tasks" in tables
    assert "executions" in tables
    assert "gate_results" in tables
    assert "events" in tables


def test_task_record_fields():
    task = TaskRecord(
        id="task-001",
        repo="/path/to/repo",
        description="Implement feature X",
        status="queued",
        workflow="default",
    )
    assert task.id == "task-001"
    assert task.status == "queued"


def test_execution_record_fields():
    execution = ExecutionRecord(
        task_id="task-001",
        stage="plan",
        agent="architect",
        model="anthropic/claude-opus-4-6",
        worktree_path="/tmp/worktree",
    )
    assert execution.agent == "architect"
    assert execution.task_id == "task-001"


def test_event_record_fields():
    event = EventRecord(
        task_id="task-001",
        execution_id=1,
        event_type="action",
        payload={"tool": "code", "action": "read_file"},
    )
    assert event.event_type == "action"
    assert event.payload["tool"] == "code"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_store_models.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create store package init**

```python
# src/agent_fleet/store/__init__.py
```

- [ ] **Step 4: Implement database.py**

```python
# src/agent_fleet/store/database.py
"""Database engine and session factory."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agent_fleet.db")


def get_engine(url: str | None = None):
    """Create SQLAlchemy engine."""
    return create_engine(url or DATABASE_URL, echo=False)


def get_session_factory(url: str | None = None):
    """Create session factory."""
    engine = get_engine(url)
    return sessionmaker(bind=engine)
```

- [ ] **Step 5: Implement models.py**

```python
# src/agent_fleet/store/models.py
"""SQLAlchemy ORM models for Agent Fleet state store."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repo: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    workflow: Mapped[str] = mapped_column(String(128), default="default")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ExecutionRecord(Base):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.id"))
    stage: Mapped[str] = mapped_column(String(128))
    agent: Mapped[str] = mapped_column(String(128))
    model: Mapped[str] = mapped_column(String(128))
    worktree_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    files_changed: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class GateResultRecord(Base):
    __tablename__ = "gate_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(Integer, ForeignKey("executions.id"))
    gate_type: Mapped[str] = mapped_column(String(32))
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class EventRecord(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.id"))
    execution_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("executions.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_store_models.py -v`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add src/agent_fleet/store/ tests/unit/test_store_models.py
git commit -m "feat(store): add SQLAlchemy ORM models for state store"
```

---

### Task 5: Repository (CRUD operations)

**Files:**
- Create: `src/agent_fleet/store/repository.py`
- Create: `tests/unit/test_repository.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_repository.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from agent_fleet.store.models import Base
from agent_fleet.store.repository import TaskRepository, ExecutionRepository, EventRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestTaskRepository:
    def test_create_task(self, db_session):
        repo = TaskRepository(db_session)
        task = repo.create(
            task_id="task-001",
            repo_path="/path/to/repo",
            description="Test task",
            workflow="default",
        )
        assert task.id == "task-001"
        assert task.status == "queued"

    def test_get_task(self, db_session):
        repo = TaskRepository(db_session)
        repo.create(task_id="task-002", repo_path="/repo", description="Test", workflow="default")
        task = repo.get("task-002")
        assert task is not None
        assert task.description == "Test"

    def test_get_nonexistent_returns_none(self, db_session):
        repo = TaskRepository(db_session)
        assert repo.get("nope") is None

    def test_update_status(self, db_session):
        repo = TaskRepository(db_session)
        repo.create(task_id="task-003", repo_path="/repo", description="Test", workflow="default")
        repo.update_status("task-003", "running")
        task = repo.get("task-003")
        assert task.status == "running"

    def test_list_by_status(self, db_session):
        repo = TaskRepository(db_session)
        repo.create(task_id="t1", repo_path="/r", description="A", workflow="default")
        repo.create(task_id="t2", repo_path="/r", description="B", workflow="default")
        repo.update_status("t1", "running")
        queued = repo.list_by_status("queued")
        assert len(queued) == 1
        assert queued[0].id == "t2"


class TestEventRepository:
    def test_append_event(self, db_session):
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

    def test_list_events_for_task(self, db_session):
        task_repo = TaskRepository(db_session)
        task_repo.create(task_id="task-e2", repo_path="/r", description="T", workflow="default")
        event_repo = EventRepository(db_session)
        event_repo.append(task_id="task-e2", event_type="action", payload={"a": 1})
        event_repo.append(task_id="task-e2", event_type="observation", payload={"b": 2})
        events = event_repo.list_for_task("task-e2")
        assert len(events) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_repository.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement repository.py**

```python
# src/agent_fleet/store/repository.py
"""CRUD operations for Agent Fleet state store."""

from sqlalchemy.orm import Session

from agent_fleet.store.models import (
    TaskRecord,
    ExecutionRecord,
    GateResultRecord,
    EventRecord,
)


class TaskRepository:
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
        return task

    def get(self, task_id: str) -> TaskRecord | None:
        return self._session.get(TaskRecord, task_id)

    def update_status(self, task_id: str, status: str) -> None:
        task = self.get(task_id)
        if task:
            task.status = status
            self._session.commit()

    def list_by_status(self, status: str) -> list[TaskRecord]:
        return list(
            self._session.query(TaskRecord).filter(TaskRecord.status == status).all()
        )


class ExecutionRepository:
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


class GateResultRepository:
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
        return result


class EventRepository:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_repository.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/agent_fleet/store/repository.py tests/unit/test_repository.py
git commit -m "feat(store): add repository CRUD operations"
```

---

## Chunk 3: Agent Registry & Config Loading

### Task 6: Agent config model

**Files:**
- Create: `src/agent_fleet/agents/__init__.py`
- Create: `src/agent_fleet/agents/base.py`
- Create: `tests/unit/test_agent_base.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_agent_base.py
import pytest
from agent_fleet.agents.base import AgentConfig


def test_parse_minimal_config():
    config = AgentConfig(
        name="Architect",
        description="Designs solutions",
        capabilities=["code_analysis"],
        tools=["code"],
        default_model="anthropic/claude-opus-4-6",
        system_prompt="You are an architect.",
    )
    assert config.name == "Architect"
    assert config.max_retries == 2
    assert config.timeout_minutes == 30
    assert config.max_tokens == 100000
    assert config.can_delegate == []


def test_parse_full_config():
    config = AgentConfig(
        name="Architect",
        description="Designs solutions",
        capabilities=["code_analysis", "task_decomposition"],
        tools=["code", "search"],
        default_model="anthropic/claude-opus-4-6",
        system_prompt="You are an architect.",
        max_retries=3,
        timeout_minutes=60,
        max_tokens=200000,
        can_delegate=["backend-dev", "frontend-dev"],
    )
    assert config.max_retries == 3
    assert config.can_delegate == ["backend-dev", "frontend-dev"]


def test_invalid_config_missing_required():
    with pytest.raises(Exception):
        AgentConfig(name="Bad")  # type: ignore
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_agent_base.py -v`
Expected: FAIL

- [ ] **Step 3: Implement base.py**

```python
# src/agent_fleet/agents/base.py
"""Agent configuration model parsed from YAML."""

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for a single agent, loaded from YAML."""

    name: str
    description: str
    capabilities: list[str]
    tools: list[str]
    default_model: str
    system_prompt: str
    max_retries: int = Field(default=2)
    timeout_minutes: int = Field(default=30)
    max_tokens: int = Field(default=100000)
    can_delegate: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_agent_base.py -v`
Expected: 3 passed

- [ ] **Step 5: Create agents/__init__.py**

```python
# src/agent_fleet/agents/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add src/agent_fleet/agents/ tests/unit/test_agent_base.py
git commit -m "feat(agents): add AgentConfig Pydantic model"
```

---

### Task 7: Agent registry (YAML loader)

**Files:**
- Create: `src/agent_fleet/agents/registry.py`
- Create: `config/agents/architect.yaml`
- Create: `tests/unit/test_registry.py`
- Create: `tests/fixtures/agents/test-agent.yaml`

- [ ] **Step 1: Create test fixture YAML**

```yaml
# tests/fixtures/agents/test-agent.yaml
name: "Test Agent"
description: "A test agent for unit tests"
capabilities:
  - testing
tools:
  - code
  - shell
default_model: "anthropic/claude-sonnet-4-6"
system_prompt: "You are a test agent."
max_retries: 1
timeout_minutes: 5
```

- [ ] **Step 2: Write failing test**

```python
# tests/unit/test_registry.py
import pytest
from pathlib import Path

from agent_fleet.agents.registry import AgentRegistry
from agent_fleet.exceptions import AgentNotFoundError

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "agents"


def test_load_agents_from_directory():
    registry = AgentRegistry(FIXTURES_DIR)
    agents = registry.list_agents()
    assert len(agents) >= 1
    assert "test-agent" in agents


def test_get_agent_config():
    registry = AgentRegistry(FIXTURES_DIR)
    config = registry.get("test-agent")
    assert config.name == "Test Agent"
    assert config.default_model == "anthropic/claude-sonnet-4-6"
    assert "code" in config.tools


def test_get_nonexistent_raises():
    registry = AgentRegistry(FIXTURES_DIR)
    with pytest.raises(AgentNotFoundError):
        registry.get("nonexistent-agent")


def test_agent_key_is_filename_stem():
    registry = AgentRegistry(FIXTURES_DIR)
    # File is test-agent.yaml, key should be "test-agent"
    assert "test-agent" in registry.list_agents()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_registry.py -v`
Expected: FAIL

- [ ] **Step 4: Implement registry.py**

```python
# src/agent_fleet/agents/registry.py
"""Load and validate agent definitions from YAML files."""

from pathlib import Path

import yaml

from agent_fleet.agents.base import AgentConfig
from agent_fleet.exceptions import AgentNotFoundError


class AgentRegistry:
    """Registry of agent configurations loaded from a directory of YAML files."""

    def __init__(self, config_dir: Path) -> None:
        self._agents: dict[str, AgentConfig] = {}
        self._load(config_dir)

    def _load(self, config_dir: Path) -> None:
        if not config_dir.is_dir():
            return
        for yaml_file in sorted(config_dir.glob("*.yaml")):
            key = yaml_file.stem
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            self._agents[key] = AgentConfig(**data)

    def get(self, agent_name: str) -> AgentConfig:
        if agent_name not in self._agents:
            raise AgentNotFoundError(agent_name)
        return self._agents[agent_name]

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    def has(self, agent_name: str) -> bool:
        return agent_name in self._agents
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_registry.py -v`
Expected: 4 passed

- [ ] **Step 6: Create built-in agent YAMLs**

Create all 6 agent definitions in `config/agents/`:

```yaml
# config/agents/architect.yaml
name: "Architect"
description: "Analyzes codebase, designs solutions, creates implementation plans. Breaks complex tasks into subtasks for other agents."
capabilities:
  - code_analysis
  - architecture_design
  - task_decomposition
tools:
  - code
  - search
default_model: "anthropic/claude-opus-4-6"
system_prompt: |
  You are a senior software architect. Analyze the codebase structure,
  understand existing patterns and conventions, and create a detailed
  implementation plan. Break complex tasks into subtasks that can be
  assigned to specialized agents (backend-dev, frontend-dev, etc.).
  Your plan must include: files to create/modify, approach, and testing strategy.
max_retries: 2
timeout_minutes: 30
max_tokens: 100000
can_delegate:
  - backend-dev
  - frontend-dev
```

```yaml
# config/agents/backend-dev.yaml
name: "Backend Dev"
description: "Implements API endpoints, services, database operations, and server-side logic."
capabilities:
  - backend_development
  - api_design
  - database_operations
tools:
  - code
  - shell
default_model: "anthropic/claude-sonnet-4-6"
system_prompt: |
  You are a backend developer. Implement server-side code following
  existing codebase patterns. Write clean, tested code. Run tests
  after implementation to verify correctness. Follow the project's
  coding conventions and architecture patterns.
max_retries: 2
timeout_minutes: 30
max_tokens: 100000
can_delegate: []
```

```yaml
# config/agents/frontend-dev.yaml
name: "Frontend Dev"
description: "Implements React UI components, pages, hooks, and frontend logic."
capabilities:
  - frontend_development
  - react_components
  - ui_implementation
tools:
  - code
  - shell
  - browser
default_model: "anthropic/claude-sonnet-4-6"
system_prompt: |
  You are a frontend developer specializing in React. Build UI
  components, pages, and hooks following the project's frontend
  conventions. Use data-testid attributes on all interactive elements.
  Write unit tests with React Testing Library.
max_retries: 2
timeout_minutes: 30
max_tokens: 100000
can_delegate: []
```

```yaml
# config/agents/reviewer.yaml
name: "Reviewer"
description: "Reviews code for bugs, security vulnerabilities, code quality, and adherence to project conventions."
capabilities:
  - code_review
  - security_analysis
  - quality_assessment
tools:
  - code
  - search
default_model: "anthropic/claude-opus-4-6"
system_prompt: |
  You are a senior code reviewer. Review the changes for:
  1. Bugs and logic errors
  2. Security vulnerabilities (OWASP top 10)
  3. Code quality and readability
  4. Adherence to project conventions
  5. Test coverage adequacy
  Produce a structured review with a score 0-100 and reasoning.
  Output format: { "score": N, "reasoning": "...", "issues": [...] }
max_retries: 1
timeout_minutes: 20
max_tokens: 50000
can_delegate: []
```

```yaml
# config/agents/tester.yaml
name: "Tester"
description: "Writes and runs tests — unit tests, integration tests, and E2E tests."
capabilities:
  - testing
  - test_writing
  - e2e_testing
tools:
  - code
  - shell
  - browser
default_model: "anthropic/claude-sonnet-4-6"
system_prompt: |
  You are a test engineer. Write comprehensive tests covering:
  1. Happy path
  2. Edge cases
  3. Error scenarios
  Run all tests and report results. If tests fail, investigate
  the root cause and fix the test or flag the implementation issue.
max_retries: 2
timeout_minutes: 30
max_tokens: 100000
can_delegate: []
```

```yaml
# config/agents/integrator.yaml
name: "Integrator"
description: "Merges agent worktrees, resolves conflicts, and creates pull requests."
capabilities:
  - git_operations
  - merge_resolution
  - pr_creation
tools:
  - code
  - shell
default_model: "anthropic/claude-sonnet-4-6"
system_prompt: |
  You are a release engineer. Merge all agent branches into the
  task branch in alphabetical order by stage name. Resolve any
  merge conflicts intelligently by understanding the intent of
  both changes. Create a pull request with a summary of all
  changes made by each agent.
max_retries: 2
timeout_minutes: 15
max_tokens: 50000
can_delegate: []
```

- [ ] **Step 7: Commit**

```bash
git add src/agent_fleet/agents/registry.py config/agents/ tests/
git commit -m "feat(agents): add agent registry with YAML loader and 6 built-in agents"
```

---

### Task 8: Workflow config loader

**Files:**
- Create: `src/agent_fleet/core/__init__.py`
- Create: `src/agent_fleet/core/workflow.py`
- Create: `config/workflows/default.yaml`
- Create: `tests/unit/test_workflow.py`
- Create: `tests/fixtures/workflows/test-workflow.yaml`

- [ ] **Step 1: Create test fixture**

```yaml
# tests/fixtures/workflows/test-workflow.yaml
name: "Test Pipeline"
concurrency: 1
max_cost_usd: 10.0
stages:
  - name: plan
    agent: architect
    gate:
      type: approval

  - name: backend
    agent: backend-dev
    depends_on: plan
    gate:
      type: automated
      checks:
        - tests_pass

  - name: frontend
    agent: frontend-dev
    depends_on: plan
    gate:
      type: automated
      checks:
        - tests_pass

  - name: review
    agent: reviewer
    depends_on:
      - backend
      - frontend
    gate:
      type: score
      min_score: 80
      on_fail: route_to
      route_target: backend
```

- [ ] **Step 2: Write failing test**

```python
# tests/unit/test_workflow.py
import pytest
from pathlib import Path

from agent_fleet.core.workflow import WorkflowConfig, StageConfig, GateConfig, load_workflow

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "workflows"


def test_load_workflow_from_yaml():
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    assert wf.name == "Test Pipeline"
    assert wf.concurrency == 1
    assert wf.max_cost_usd == 10.0
    assert len(wf.stages) == 4


def test_stage_depends_on_normalized_to_list():
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    plan = wf.get_stage("plan")
    assert plan.depends_on == []
    backend = wf.get_stage("backend")
    assert backend.depends_on == ["plan"]
    review = wf.get_stage("review")
    assert set(review.depends_on) == {"backend", "frontend"}


def test_parallel_stages_detected():
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    # backend and frontend both depend_on plan -> they're parallel
    ready = wf.get_ready_stages(completed={"plan"})
    names = {s.name for s in ready}
    assert names == {"backend", "frontend"}


def test_no_stages_ready_when_deps_unmet():
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    ready = wf.get_ready_stages(completed=set())
    names = {s.name for s in ready}
    assert names == {"plan"}  # plan has no deps


def test_gate_config_parsed():
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    review = wf.get_stage("review")
    assert review.gate.type == "score"
    assert review.gate.min_score == 80
    assert review.gate.on_fail == "route_to"
    assert review.gate.route_target == "backend"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_workflow.py -v`
Expected: FAIL

- [ ] **Step 4: Implement workflow.py**

```python
# src/agent_fleet/core/workflow.py
"""Workflow configuration model and loader."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class GateConfig(BaseModel):
    type: str  # automated, score, approval, custom
    checks: list[str] = Field(default_factory=list)
    min_score: int | None = None
    scored_by: str = "reviewer"
    on_fail: str = "retry"  # retry, route_to, halt
    route_target: str | None = None
    max_retries: int | None = None


class ReactionConfig(BaseModel):
    action: str
    retries: int = 1


class StageConfig(BaseModel):
    name: str
    agent: str
    model: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    gate: GateConfig = Field(default_factory=lambda: GateConfig(type="automated"))
    reactions: dict[str, ReactionConfig] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_depends_on(cls, data: dict) -> dict:
        deps = data.get("depends_on")
        if deps is None:
            data["depends_on"] = []
        elif isinstance(deps, str):
            data["depends_on"] = [deps]
        return data


class WorkflowConfig(BaseModel):
    name: str
    concurrency: int = 1
    max_cost_usd: float | None = None
    classifier_mode: str = "suggest"  # suggest, override, disabled
    stages: list[StageConfig]

    def get_stage(self, name: str) -> StageConfig:
        for stage in self.stages:
            if stage.name == name:
                return stage
        raise ValueError(f"Stage not found: {name}")

    def get_ready_stages(self, completed: set[str]) -> list[StageConfig]:
        """Return stages whose dependencies are all in the completed set."""
        ready = []
        for stage in self.stages:
            if stage.name in completed:
                continue
            if all(dep in completed for dep in stage.depends_on):
                ready.append(stage)
        return ready


def load_workflow(path: Path) -> WorkflowConfig:
    """Load a workflow config from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return WorkflowConfig(**data)
```

- [ ] **Step 5: Create core/__init__.py**

```python
# src/agent_fleet/core/__init__.py
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_workflow.py -v`
Expected: 5 passed

- [ ] **Step 7: Create default workflow YAML**

```yaml
# config/workflows/default.yaml
name: "Full Development Pipeline"
concurrency: 1
max_cost_usd: 50.0
classifier_mode: suggest
stages:
  - name: plan
    agent: architect
    model: anthropic/claude-opus-4-6
    gate:
      type: approval

  - name: backend
    agent: backend-dev
    depends_on: plan
    gate:
      type: automated
      checks:
        - tests_pass
        - lint_clean

  - name: frontend
    agent: frontend-dev
    depends_on: plan
    gate:
      type: automated
      checks:
        - tests_pass
        - lint_clean

  - name: review
    agent: reviewer
    model: anthropic/claude-opus-4-6
    depends_on:
      - backend
      - frontend
    gate:
      type: score
      min_score: 80
      on_fail: route_to
      route_target: backend
      max_retries: 2

  - name: e2e
    agent: tester
    depends_on: review
    gate:
      type: automated
      checks:
        - all_tests_pass

  - name: deliver
    agent: integrator
    depends_on: e2e
    actions:
      - merge_worktrees
      - create_pr
```

- [ ] **Step 8: Commit**

```bash
git add src/agent_fleet/core/ config/workflows/ tests/
git commit -m "feat(core): add workflow config loader with DAG-based stage resolution"
```

---

## Chunk 4: LLM Provider & Tools

### Task 9: LiteLLM provider wrapper

**Files:**
- Create: `src/agent_fleet/models/__init__.py`
- Create: `src/agent_fleet/models/provider.py`
- Create: `tests/unit/test_provider.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_provider.py
import pytest
from unittest.mock import patch, MagicMock

from agent_fleet.models.provider import LLMProvider, LLMResponse


def test_llm_response_model():
    resp = LLMResponse(
        content="Hello world",
        model="anthropic/claude-sonnet-4-6",
        tokens_used=150,
        cost_usd=0.003,
    )
    assert resp.content == "Hello world"
    assert resp.tokens_used == 150


@patch("agent_fleet.models.provider.litellm_completion")
def test_completion_calls_litellm(mock_completion):
    mock_choice = MagicMock()
    mock_choice.message.content = "Test response"
    mock_result = MagicMock()
    mock_result.choices = [mock_choice]
    mock_result.model = "anthropic/claude-sonnet-4-6"
    mock_result.usage.total_tokens = 200
    mock_completion.return_value = mock_result

    provider = LLMProvider()
    result = provider.complete(
        model="anthropic/claude-sonnet-4-6",
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert result.content == "Test response"
    mock_completion.assert_called_once()


@patch("agent_fleet.models.provider.litellm_completion")
def test_completion_tracks_token_usage(mock_completion):
    mock_choice = MagicMock()
    mock_choice.message.content = "Response"
    mock_result = MagicMock()
    mock_result.choices = [mock_choice]
    mock_result.model = "test-model"
    mock_result.usage.total_tokens = 500
    mock_completion.return_value = mock_result

    provider = LLMProvider()
    provider.complete(model="test-model", messages=[{"role": "user", "content": "Hi"}])
    assert provider.total_tokens_used == 500

    provider.complete(model="test-model", messages=[{"role": "user", "content": "Hi"}])
    assert provider.total_tokens_used == 1000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_provider.py -v`
Expected: FAIL

- [ ] **Step 3: Implement provider.py**

```python
# src/agent_fleet/models/provider.py
"""LiteLLM wrapper for unified model access."""

import structlog
from litellm import completion as litellm_completion
from pydantic import BaseModel

from agent_fleet.exceptions import LLMProviderError

logger = structlog.get_logger()


class LLMResponse(BaseModel):
    content: str
    model: str
    tokens_used: int
    cost_usd: float = 0.0


class LLMProvider:
    """Unified LLM provider using LiteLLM."""

    def __init__(self) -> None:
        self.total_tokens_used: int = 0
        self.total_cost_usd: float = 0.0

    def complete(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Call an LLM via LiteLLM."""
        try:
            kwargs: dict = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if tools:
                kwargs["tools"] = tools

            result = litellm_completion(**kwargs)

            tokens = result.usage.total_tokens if result.usage else 0
            self.total_tokens_used += tokens

            content = result.choices[0].message.content or ""

            response = LLMResponse(
                content=content,
                model=result.model or model,
                tokens_used=tokens,
            )

            logger.info(
                "llm_completion",
                model=model,
                tokens=tokens,
            )

            return response

        except Exception as e:
            logger.error("llm_completion_failed", model=model, error=str(e))
            raise LLMProviderError(f"LLM call failed: {e}") from e

    def within_budget(self, max_tokens: int) -> bool:
        """Check if total token usage is within budget."""
        return self.total_tokens_used < max_tokens
```

- [ ] **Step 4: Create models/__init__.py**

```python
# src/agent_fleet/models/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_provider.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/agent_fleet/models/ tests/unit/test_provider.py
git commit -m "feat(models): add LiteLLM provider wrapper with token tracking"
```

---

### Task 10: BaseTool and code/shell tools

**Files:**
- Create: `src/agent_fleet/tools/__init__.py`
- Create: `src/agent_fleet/tools/base.py`
- Create: `src/agent_fleet/tools/code.py`
- Create: `src/agent_fleet/tools/shell.py`
- Create: `tests/unit/test_tools.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_tools.py
import pytest
import tempfile
from pathlib import Path

from agent_fleet.tools.base import BaseTool
from agent_fleet.tools.code import ReadFileTool, WriteFileTool, ListFilesTool
from agent_fleet.tools.shell import ShellTool


class TestBaseTool:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            BaseTool()  # type: ignore


class TestReadFileTool:
    def test_read_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        tool = ReadFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "test.txt"})
        assert result["content"] == "hello world"

    def test_read_outside_workspace_blocked(self, tmp_path):
        tool = ReadFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "/etc/passwd"})
        assert "error" in result

    def test_read_nonexistent_file(self, tmp_path):
        tool = ReadFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "nope.txt"})
        assert "error" in result


class TestWriteFileTool:
    def test_write_file(self, tmp_path):
        tool = WriteFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "out.txt", "content": "written"})
        assert result["success"] is True
        assert (tmp_path / "out.txt").read_text() == "written"

    def test_write_creates_parent_dirs(self, tmp_path):
        tool = WriteFileTool(workspace_root=tmp_path)
        tool.execute({"path": "sub/dir/file.txt", "content": "deep"})
        assert (tmp_path / "sub" / "dir" / "file.txt").read_text() == "deep"

    def test_write_outside_workspace_blocked(self, tmp_path):
        tool = WriteFileTool(workspace_root=tmp_path)
        result = tool.execute({"path": "/tmp/evil.txt", "content": "bad"})
        assert "error" in result


class TestShellTool:
    def test_run_simple_command(self, tmp_path):
        tool = ShellTool(workspace_root=tmp_path)
        result = tool.execute({"command": "echo hello"})
        assert "hello" in result["stdout"]
        assert result["returncode"] == 0

    def test_run_failing_command(self, tmp_path):
        tool = ShellTool(workspace_root=tmp_path)
        result = tool.execute({"command": "false"})
        assert result["returncode"] != 0

    def test_cwd_is_workspace(self, tmp_path):
        tool = ShellTool(workspace_root=tmp_path)
        result = tool.execute({"command": "pwd"})
        assert str(tmp_path) in result["stdout"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_tools.py -v`
Expected: FAIL

- [ ] **Step 3: Implement base.py**

```python
# src/agent_fleet/tools/base.py
"""Base tool interface for Agent Fleet."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseTool(ABC):
    """Abstract base for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used by the LLM."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description used by the LLM."""
        ...

    @abstractmethod
    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool and return results."""
        ...

    @abstractmethod
    def schema(self) -> dict:
        """JSON schema for the tool's parameters."""
        ...

    def _validate_path(self, workspace_root: Path, requested: str) -> Path | None:
        """Resolve a path and ensure it's within the workspace."""
        resolved = (workspace_root / requested).resolve()
        if not str(resolved).startswith(str(workspace_root.resolve())):
            return None
        return resolved
```

- [ ] **Step 4: Implement code.py**

```python
# src/agent_fleet/tools/code.py
"""Code tools — file read, write, list."""

from pathlib import Path
from typing import Any

from agent_fleet.tools.base import BaseTool


class ReadFileTool(BaseTool):
    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file"

    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        target = self._validate_path(self._root, input["path"])
        if target is None:
            return {"error": "Path is outside workspace"}
        if not target.exists():
            return {"error": f"File not found: {input['path']}"}
        return {"content": target.read_text()}

    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path relative to workspace"}},
            "required": ["path"],
        }


class WriteFileTool(BaseTool):
    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file"

    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        target = self._validate_path(self._root, input["path"])
        if target is None:
            return {"error": "Path is outside workspace"}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(input["content"])
        return {"success": True, "path": str(target.relative_to(self._root))}

    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        }


class ListFilesTool(BaseTool):
    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files in a directory"

    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        target_dir = self._validate_path(self._root, input.get("path", "."))
        if target_dir is None:
            return {"error": "Path is outside workspace"}
        if not target_dir.is_dir():
            return {"error": "Not a directory"}
        files = [str(f.relative_to(self._root)) for f in sorted(target_dir.rglob("*")) if f.is_file()]
        return {"files": files[:500]}  # cap at 500

    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Directory path, default '.'"}},
        }
```

- [ ] **Step 5: Implement shell.py**

```python
# src/agent_fleet/tools/shell.py
"""Shell tool — sandboxed command execution."""

import subprocess
from pathlib import Path
from typing import Any

from agent_fleet.tools.base import BaseTool


class ShellTool(BaseTool):
    def __init__(self, workspace_root: Path, timeout_seconds: int = 120) -> None:
        self._root = workspace_root
        self._timeout = timeout_seconds

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return "Run a shell command in the workspace directory"

    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        command = input["command"]
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {self._timeout}s", "returncode": -1}

    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Shell command to run"}},
            "required": ["command"],
        }
```

- [ ] **Step 6: Create tools/__init__.py**

```python
# src/agent_fleet/tools/__init__.py
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_tools.py -v`
Expected: 10 passed

- [ ] **Step 8: Commit**

```bash
git add src/agent_fleet/tools/ tests/unit/test_tools.py
git commit -m "feat(tools): add BaseTool interface, code tools, and shell tool"
```

---

## Chunk 5: Workspace (Git Worktrees)

### Task 11: Git worktree manager

**Files:**
- Create: `src/agent_fleet/workspace/__init__.py`
- Create: `src/agent_fleet/workspace/worktree.py`
- Create: `tests/unit/test_worktree.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_worktree.py
import pytest
import subprocess
from pathlib import Path

from agent_fleet.workspace.worktree import WorktreeManager


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repo with an initial commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    (tmp_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
    return tmp_path


def test_create_worktree(git_repo):
    mgr = WorktreeManager(git_repo)
    wt_path = mgr.create(task_id="task-001", stage="backend")
    assert wt_path.exists()
    assert (wt_path / "README.md").exists()


def test_worktree_on_correct_branch(git_repo):
    mgr = WorktreeManager(git_repo)
    wt_path = mgr.create(task_id="task-002", stage="frontend")
    result = subprocess.run(
        ["git", "branch", "--show-current"], cwd=wt_path, capture_output=True, text=True
    )
    assert "fleet/task-002/frontend" in result.stdout.strip()


def test_cleanup_worktree(git_repo):
    mgr = WorktreeManager(git_repo)
    wt_path = mgr.create(task_id="task-003", stage="plan")
    mgr.cleanup(wt_path)
    assert not wt_path.exists()


def test_list_worktrees(git_repo):
    mgr = WorktreeManager(git_repo)
    mgr.create(task_id="task-004", stage="a")
    mgr.create(task_id="task-004", stage="b")
    worktrees = mgr.list_worktrees()
    assert len(worktrees) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_worktree.py -v`
Expected: FAIL

- [ ] **Step 3: Implement worktree.py**

```python
# src/agent_fleet/workspace/worktree.py
"""Git worktree management for agent isolation."""

import subprocess
from pathlib import Path

import structlog

from agent_fleet.exceptions import WorktreeError

logger = structlog.get_logger()


class WorktreeManager:
    """Manages git worktrees for agent task isolation."""

    def __init__(self, repo_root: Path) -> None:
        self._repo = repo_root
        self._worktrees_dir = repo_root / ".fleet-worktrees"
        self._worktrees_dir.mkdir(exist_ok=True)

    def create(self, task_id: str, stage: str) -> Path:
        """Create a new worktree for a task stage."""
        branch_name = f"fleet/{task_id}/{stage}"
        worktree_name = f"fleet-worktree-{task_id}-{stage}"
        worktree_path = self._worktrees_dir / worktree_name

        try:
            # Create branch from current HEAD
            self._run_git("branch", branch_name)
        except WorktreeError:
            pass  # Branch may already exist

        try:
            self._run_git("worktree", "add", str(worktree_path), branch_name)
        except WorktreeError as e:
            raise WorktreeError(f"Failed to create worktree: {e}") from e

        logger.info("worktree_created", task_id=task_id, stage=stage, path=str(worktree_path))
        return worktree_path

    def cleanup(self, worktree_path: Path) -> None:
        """Remove a worktree and its branch."""
        try:
            self._run_git("worktree", "remove", str(worktree_path), "--force")
        except WorktreeError:
            # Manual cleanup if git worktree remove fails
            import shutil
            if worktree_path.exists():
                shutil.rmtree(worktree_path)
            self._run_git("worktree", "prune")

        logger.info("worktree_cleaned", path=str(worktree_path))

    def list_worktrees(self) -> list[Path]:
        """List all active worktrees."""
        result = self._run_git("worktree", "list", "--porcelain")
        paths = []
        for line in result.splitlines():
            if line.startswith("worktree "):
                p = Path(line.split(" ", 1)[1])
                if p != self._repo:
                    paths.append(p)
        return paths

    def cleanup_all(self, task_id: str) -> None:
        """Remove all worktrees for a task."""
        for wt in self.list_worktrees():
            if f"fleet-worktree-{task_id}" in wt.name:
                self.cleanup(wt)

    def _run_git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=str(self._repo),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout
```

- [ ] **Step 4: Create workspace/__init__.py**

```python
# src/agent_fleet/workspace/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_worktree.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/agent_fleet/workspace/ tests/unit/test_worktree.py
git commit -m "feat(workspace): add git worktree manager for agent isolation"
```

---

## Chunk 6: Core Orchestrator

### Task 12: Graph state schema

**Files:**
- Create: `src/agent_fleet/core/state.py`
- Create: `tests/unit/test_state.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_state.py
from agent_fleet.core.state import FleetState


def test_initial_state():
    state = FleetState(
        task_id="task-001",
        repo="/path/to/repo",
        description="Implement feature",
        workflow_name="default",
    )
    assert state.status == "queued"
    assert state.completed_stages == []
    assert state.current_stage is None
    assert state.retry_counts == {}


def test_state_tracks_completed_stages():
    state = FleetState(
        task_id="task-001",
        repo="/path",
        description="Test",
        workflow_name="default",
        completed_stages=["plan", "backend"],
    )
    assert "plan" in state.completed_stages
    assert len(state.completed_stages) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_state.py -v`
Expected: FAIL

- [ ] **Step 3: Implement state.py**

```python
# src/agent_fleet/core/state.py
"""LangGraph state schema for the orchestrator."""

from typing import TypedDict


class FleetState(TypedDict, total=False):
    # Task identity
    task_id: str
    repo: str
    description: str
    workflow_name: str

    # Progress
    status: str  # queued, running, completed, error, interrupted
    current_stage: str | None
    completed_stages: list[str]
    retry_counts: dict[str, int]  # stage_name -> retry count

    # Agent outputs
    stage_outputs: dict[str, dict]  # stage_name -> agent output
    stage_errors: dict[str, str]  # stage_name -> error message

    # Budget
    total_tokens: int
    total_cost_usd: float

    # Result
    pr_url: str | None
    error_message: str | None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_state.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/agent_fleet/core/state.py tests/unit/test_state.py
git commit -m "feat(core): add LangGraph state schema"
```

---

### Task 13: Gate evaluation

**Files:**
- Create: `src/agent_fleet/core/gates.py`
- Create: `tests/unit/test_gates.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_gates.py
import pytest
from agent_fleet.core.gates import evaluate_gate, GateResult
from agent_fleet.core.workflow import GateConfig


def test_automated_gate_passes_when_all_checks_pass():
    gate = GateConfig(type="automated", checks=["tests_pass", "lint_clean"])
    check_results = {"tests_pass": True, "lint_clean": True}
    result = evaluate_gate(gate, check_results=check_results)
    assert result.passed is True


def test_automated_gate_fails_when_check_fails():
    gate = GateConfig(type="automated", checks=["tests_pass"])
    check_results = {"tests_pass": False}
    result = evaluate_gate(gate, check_results=check_results)
    assert result.passed is False
    assert "tests_pass" in result.reason


def test_score_gate_passes_above_threshold():
    gate = GateConfig(type="score", min_score=80)
    result = evaluate_gate(gate, score=85)
    assert result.passed is True


def test_score_gate_fails_below_threshold():
    gate = GateConfig(type="score", min_score=80)
    result = evaluate_gate(gate, score=60)
    assert result.passed is False
    assert "60" in result.reason


def test_approval_gate_passes_when_approved():
    gate = GateConfig(type="approval")
    result = evaluate_gate(gate, approved=True)
    assert result.passed is True


def test_approval_gate_fails_when_not_approved():
    gate = GateConfig(type="approval")
    result = evaluate_gate(gate, approved=False)
    assert result.passed is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_gates.py -v`
Expected: FAIL

- [ ] **Step 3: Implement gates.py**

```python
# src/agent_fleet/core/gates.py
"""Gate evaluation logic for quality checkpoints."""

from dataclasses import dataclass

import structlog

from agent_fleet.core.workflow import GateConfig

logger = structlog.get_logger()


@dataclass
class GateResult:
    passed: bool
    gate_type: str
    reason: str
    details: dict | None = None


def evaluate_gate(
    gate: GateConfig,
    check_results: dict[str, bool] | None = None,
    score: int | None = None,
    approved: bool | None = None,
    custom_result: bool | None = None,
) -> GateResult:
    """Evaluate a quality gate and return the result."""

    if gate.type == "automated":
        return _evaluate_automated(gate, check_results or {})
    elif gate.type == "score":
        return _evaluate_score(gate, score)
    elif gate.type == "approval":
        return _evaluate_approval(gate, approved)
    elif gate.type == "custom":
        return GateResult(
            passed=custom_result or False,
            gate_type="custom",
            reason="Custom gate evaluation",
        )
    else:
        return GateResult(passed=False, gate_type=gate.type, reason=f"Unknown gate type: {gate.type}")


def _evaluate_automated(gate: GateConfig, check_results: dict[str, bool]) -> GateResult:
    failed_checks = [name for name in gate.checks if not check_results.get(name, False)]
    if failed_checks:
        return GateResult(
            passed=False,
            gate_type="automated",
            reason=f"Failed checks: {', '.join(failed_checks)}",
            details={"check_results": check_results},
        )
    return GateResult(passed=True, gate_type="automated", reason="All checks passed")


def _evaluate_score(gate: GateConfig, score: int | None) -> GateResult:
    if score is None:
        return GateResult(passed=False, gate_type="score", reason="No score provided")
    min_score = gate.min_score or 0
    if score >= min_score:
        return GateResult(
            passed=True,
            gate_type="score",
            reason=f"Score {score} >= {min_score}",
        )
    return GateResult(
        passed=False,
        gate_type="score",
        reason=f"Score {score} < {min_score}",
        details={"score": score, "min_score": min_score},
    )


def _evaluate_approval(gate: GateConfig, approved: bool | None) -> GateResult:
    if approved:
        return GateResult(passed=True, gate_type="approval", reason="Approved")
    return GateResult(passed=False, gate_type="approval", reason="Not approved")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_gates.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/agent_fleet/core/gates.py tests/unit/test_gates.py
git commit -m "feat(core): add gate evaluation logic for all 4 gate types"
```

---

### Task 14: DAG router

**Files:**
- Create: `src/agent_fleet/core/router.py`
- Create: `tests/unit/test_router.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_router.py
from pathlib import Path
from agent_fleet.core.router import Router
from agent_fleet.core.workflow import load_workflow

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "workflows"


def test_first_stage_is_plan():
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    next_stages = router.get_next_stages(completed=set())
    assert len(next_stages) == 1
    assert next_stages[0].name == "plan"


def test_parallel_stages_after_plan():
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    next_stages = router.get_next_stages(completed={"plan"})
    names = {s.name for s in next_stages}
    assert names == {"backend", "frontend"}


def test_review_after_both_parallel():
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    next_stages = router.get_next_stages(completed={"plan", "backend", "frontend"})
    assert len(next_stages) == 1
    assert next_stages[0].name == "review"


def test_all_done_returns_empty():
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    next_stages = router.get_next_stages(completed={"plan", "backend", "frontend", "review"})
    assert len(next_stages) == 0


def test_route_back_target():
    wf = load_workflow(FIXTURES_DIR / "test-workflow.yaml")
    router = Router(wf)
    target = router.get_route_back_target("review")
    assert target == "backend"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_router.py -v`
Expected: FAIL

- [ ] **Step 3: Implement router.py**

```python
# src/agent_fleet/core/router.py
"""DAG-based stage routing for workflow execution."""

from agent_fleet.core.workflow import WorkflowConfig, StageConfig


class Router:
    """Routes tasks through workflow stages based on DAG dependencies."""

    def __init__(self, workflow: WorkflowConfig) -> None:
        self._workflow = workflow

    def get_next_stages(self, completed: set[str]) -> list[StageConfig]:
        """Return stages ready to execute (all deps met, not yet completed)."""
        return self._workflow.get_ready_stages(completed)

    def get_route_back_target(self, stage_name: str) -> str | None:
        """Get the route_to target for a failed stage's gate."""
        stage = self._workflow.get_stage(stage_name)
        if stage.gate.on_fail == "route_to":
            return stage.gate.route_target
        return None

    def is_complete(self, completed: set[str]) -> bool:
        """Check if all stages are completed."""
        all_stage_names = {s.name for s in self._workflow.stages}
        return all_stage_names <= completed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_router.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/agent_fleet/core/router.py tests/unit/test_router.py
git commit -m "feat(core): add DAG-based stage router"
```

---

### Task 15: LangGraph orchestrator

**Files:**
- Create: `src/agent_fleet/core/orchestrator.py`
- Create: `src/agent_fleet/core/events.py`
- Create: `tests/unit/test_orchestrator.py`

- [ ] **Step 1: Implement events.py** (simple helper, tested via orchestrator)

```python
# src/agent_fleet/core/events.py
"""Event logging helpers."""

import structlog

logger = structlog.get_logger()


def log_event(task_id: str, event_type: str, payload: dict) -> dict:
    """Create and log an event. Returns the event dict."""
    event = {
        "task_id": task_id,
        "event_type": event_type,
        "payload": payload,
    }
    logger.info("fleet_event", **event)
    return event
```

- [ ] **Step 2: Write failing test**

```python
# tests/unit/test_orchestrator.py
import pytest
from unittest.mock import MagicMock, patch

from agent_fleet.core.orchestrator import build_orchestrator_graph
from agent_fleet.core.state import FleetState


def test_graph_builds_without_error():
    graph = build_orchestrator_graph()
    assert graph is not None


def test_graph_has_expected_nodes():
    graph = build_orchestrator_graph()
    # The compiled graph should have our node names
    node_names = set(graph.get_graph().nodes.keys())
    assert "route_next" in node_names
    assert "execute_stage" in node_names
    assert "evaluate_gate" in node_names
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_orchestrator.py -v`
Expected: FAIL

- [ ] **Step 4: Implement orchestrator.py**

```python
# src/agent_fleet/core/orchestrator.py
"""LangGraph orchestrator — the core state graph."""

from typing import Literal

import structlog
from langgraph.graph import StateGraph, END

from agent_fleet.core.state import FleetState
from agent_fleet.core.events import log_event

logger = structlog.get_logger()


def route_next(state: FleetState) -> FleetState:
    """Determine the next stage(s) to execute."""
    log_event(state["task_id"], "route", {"completed": state.get("completed_stages", [])})
    return state


def execute_stage(state: FleetState) -> FleetState:
    """Execute the current stage's agent."""
    stage = state.get("current_stage")
    log_event(state["task_id"], "execute", {"stage": stage})
    # Agent execution will be wired in by the runner
    return state


def evaluate_gate(state: FleetState) -> FleetState:
    """Evaluate the gate for the current stage."""
    stage = state.get("current_stage")
    log_event(state["task_id"], "gate", {"stage": stage})
    return state


def should_continue(state: FleetState) -> Literal["route_next", "__end__"]:
    """Decide whether to continue or finish."""
    status = state.get("status", "running")
    if status in ("completed", "error", "interrupted", "cost_limit"):
        return "__end__"
    return "route_next"


def build_orchestrator_graph() -> StateGraph:
    """Build the LangGraph state graph for task orchestration."""
    graph = StateGraph(FleetState)

    # Add nodes
    graph.add_node("route_next", route_next)
    graph.add_node("execute_stage", execute_stage)
    graph.add_node("evaluate_gate", evaluate_gate)

    # Define edges
    graph.set_entry_point("route_next")
    graph.add_edge("route_next", "execute_stage")
    graph.add_edge("execute_stage", "evaluate_gate")
    graph.add_conditional_edges("evaluate_gate", should_continue)

    return graph.compile()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_orchestrator.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add src/agent_fleet/core/orchestrator.py src/agent_fleet/core/events.py tests/unit/test_orchestrator.py
git commit -m "feat(core): add LangGraph orchestrator with route/execute/gate cycle"
```

---

## Chunk 7: API & CLI

### Task 16: FastAPI app and task routes

**Files:**
- Create: `src/agent_fleet/api/__init__.py`
- Create: `src/agent_fleet/api/schemas.py`
- Create: `src/agent_fleet/api/routes/__init__.py`
- Create: `src/agent_fleet/api/routes/tasks.py`
- Create: `src/agent_fleet/main.py`
- Create: `tests/unit/test_api_tasks.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_api_tasks.py
import pytest
from fastapi.testclient import TestClient

from agent_fleet.main import create_app


@pytest.fixture
def client():
    app = create_app(database_url="sqlite:///:memory:")
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_submit_task(client):
    resp = client.post("/api/v1/tasks", json={
        "repo": "/path/to/repo",
        "description": "Implement feature X",
        "workflow": "default",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "queued"


def test_get_task(client):
    create = client.post("/api/v1/tasks", json={
        "repo": "/repo",
        "description": "Test",
        "workflow": "default",
    })
    task_id = create.json()["task_id"]
    resp = client.get(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["task_id"] == task_id


def test_get_nonexistent_task(client):
    resp = client.get("/api/v1/tasks/nonexistent")
    assert resp.status_code == 404


def test_list_tasks(client):
    client.post("/api/v1/tasks", json={"repo": "/r", "description": "A", "workflow": "default"})
    client.post("/api/v1/tasks", json={"repo": "/r", "description": "B", "workflow": "default"})
    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 200
    assert len(resp.json()["tasks"]) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_api_tasks.py -v`
Expected: FAIL

- [ ] **Step 3: Implement schemas.py**

```python
# src/agent_fleet/api/schemas.py
"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel, Field


class TaskSubmitRequest(BaseModel):
    repo: str
    description: str
    workflow: str = "default"


class TaskResponse(BaseModel):
    task_id: str
    repo: str
    description: str
    status: str
    workflow: str


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
```

- [ ] **Step 4: Implement task routes**

```python
# src/agent_fleet/api/routes/tasks.py
"""Task submission and management routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agent_fleet.api.schemas import TaskSubmitRequest, TaskResponse, TaskListResponse
from agent_fleet.store.repository import TaskRepository

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _task_to_response(task) -> TaskResponse:
    return TaskResponse(
        task_id=task.id,
        repo=task.repo,
        description=task.description,
        status=task.status,
        workflow=task.workflow,
    )


@router.post("", status_code=201)
def submit_task(request: TaskSubmitRequest, session: Session = Depends()) -> TaskResponse:
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    repo = TaskRepository(session)
    task = repo.create(
        task_id=task_id,
        repo_path=request.repo,
        description=request.description,
        workflow=request.workflow,
    )
    return _task_to_response(task)


@router.get("/{task_id}")
def get_task(task_id: str, session: Session = Depends()) -> TaskResponse:
    repo = TaskRepository(session)
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@router.get("")
def list_tasks(session: Session = Depends()) -> TaskListResponse:
    repo = TaskRepository(session)
    # List all tasks (could add status filter later)
    from agent_fleet.store.models import TaskRecord
    tasks = session.query(TaskRecord).order_by(TaskRecord.created_at.desc()).all()
    return TaskListResponse(tasks=[_task_to_response(t) for t in tasks])
```

- [ ] **Step 5: Create api/__init__.py and routes/__init__.py**

```python
# src/agent_fleet/api/__init__.py
```

```python
# src/agent_fleet/api/routes/__init__.py
```

- [ ] **Step 6: Implement main.py (app factory)**

```python
# src/agent_fleet/main.py
"""FastAPI application factory."""

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from agent_fleet import __version__
from agent_fleet.api.routes import tasks
from agent_fleet.api.schemas import HealthResponse
from agent_fleet.store.models import Base


def create_app(database_url: str = "sqlite:///./agent_fleet.db") -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Agent Fleet", version=__version__)

    # Database setup
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    # Override the Depends() in routes
    app.dependency_overrides[Session] = get_session

    # Routes
    app.include_router(tasks.router)

    @app.get("/health")
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    return app


# Default app for uvicorn
app = create_app()
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_api_tasks.py -v`
Expected: 5 passed

- [ ] **Step 8: Commit**

```bash
git add src/agent_fleet/api/ src/agent_fleet/main.py tests/unit/test_api_tasks.py
git commit -m "feat(api): add FastAPI app with task submission and health check"
```

---

### Task 17: CLI with Typer

**Files:**
- Create: `cli/__init__.py`
- Create: `cli/main.py`
- Create: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_cli.py
from typer.testing import CliRunner
from cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Agent Fleet" in result.stdout


def test_agents_list():
    result = runner.invoke(app, ["agents", "list"])
    assert result.exit_code == 0
    assert "architect" in result.stdout.lower()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Implement cli/main.py**

```python
# cli/main.py
"""Agent Fleet CLI — command-line interface."""

from pathlib import Path

import typer

from agent_fleet import __version__
from agent_fleet.agents.registry import AgentRegistry

app = typer.Typer(name="fleet", help="Agent Fleet — Multi-model AI agent orchestration")
agents_app = typer.Typer(help="Manage agents")
app.add_typer(agents_app, name="agents")

# Default config directory
CONFIG_DIR = Path(__file__).parent.parent / "config"


@app.command()
def version():
    """Show version."""
    typer.echo(f"Agent Fleet v{__version__}")


@app.command()
def run(
    repo: str = typer.Option(..., help="Path to the git repository"),
    task: str = typer.Option(..., help="Task description"),
    workflow: str = typer.Option("default", help="Workflow name"),
):
    """Submit a task to the agent fleet."""
    typer.echo(f"Submitting task to fleet...")
    typer.echo(f"  Repo: {repo}")
    typer.echo(f"  Task: {task}")
    typer.echo(f"  Workflow: {workflow}")
    # TODO: wire to API or direct orchestrator invocation
    typer.echo("Task submission not yet implemented — API integration coming in next phase.")


@agents_app.command("list")
def agents_list():
    """List available agents."""
    agents_dir = CONFIG_DIR / "agents"
    if not agents_dir.exists():
        typer.echo("No agents directory found.")
        raise typer.Exit(1)
    registry = AgentRegistry(agents_dir)
    for name in registry.list_agents():
        config = registry.get(name)
        typer.echo(f"  {name:20s} {config.description[:60]}")


@app.command()
def status(task_id: str = typer.Argument(..., help="Task ID")):
    """Check task status."""
    typer.echo(f"Checking status for {task_id}...")
    # TODO: wire to API
    typer.echo("Status check not yet implemented.")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Create cli/__init__.py**

```python
# cli/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/unit/test_cli.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add cli/ tests/unit/test_cli.py
git commit -m "feat(cli): add Typer CLI with agents list, run, status, version commands"
```

---

## Chunk 8: Integration — End-to-End Smoke Test

### Task 18: Integration test — full pipeline smoke test

**Files:**
- Create: `tests/integration/test_e2e_smoke.py`

This test verifies all layers work together: API accepts a task, state is persisted, agents can be loaded, workflow can be parsed, worktrees can be created.

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_e2e_smoke.py
"""Smoke test — verify all layers integrate correctly."""

import subprocess
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from agent_fleet.main import create_app
from agent_fleet.agents.registry import AgentRegistry
from agent_fleet.core.workflow import load_workflow
from agent_fleet.core.router import Router
from agent_fleet.core.gates import evaluate_gate, GateResult
from agent_fleet.core.orchestrator import build_orchestrator_graph
from agent_fleet.models.provider import LLMResponse
from agent_fleet.workspace.worktree import WorktreeManager

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestLayerIntegration:
    """Test that all layers can be instantiated and interact."""

    def test_registry_loads_all_builtin_agents(self):
        registry = AgentRegistry(CONFIG_DIR / "agents")
        agents = registry.list_agents()
        assert len(agents) == 6
        expected = {"architect", "backend-dev", "frontend-dev", "reviewer", "tester", "integrator"}
        assert set(agents) == expected

    def test_default_workflow_loads(self):
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        assert wf.name == "Full Development Pipeline"
        assert len(wf.stages) == 6

    def test_workflow_agents_exist_in_registry(self):
        registry = AgentRegistry(CONFIG_DIR / "agents")
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        for stage in wf.stages:
            assert registry.has(stage.agent), f"Agent '{stage.agent}' not in registry"

    def test_router_resolves_full_pipeline(self):
        wf = load_workflow(CONFIG_DIR / "workflows" / "default.yaml")
        router = Router(wf)

        # Simulate walking through the pipeline
        completed: set[str] = set()

        # Step 1: plan
        ready = router.get_next_stages(completed)
        assert {s.name for s in ready} == {"plan"}
        completed.add("plan")

        # Step 2: backend + frontend (parallel)
        ready = router.get_next_stages(completed)
        assert {s.name for s in ready} == {"backend", "frontend"}
        completed.update(["backend", "frontend"])

        # Step 3: review
        ready = router.get_next_stages(completed)
        assert {s.name for s in ready} == {"review"}
        completed.add("review")

        # Step 4: e2e
        ready = router.get_next_stages(completed)
        assert {s.name for s in ready} == {"e2e"}
        completed.add("e2e")

        # Step 5: deliver
        ready = router.get_next_stages(completed)
        assert {s.name for s in ready} == {"deliver"}
        completed.add("deliver")

        assert router.is_complete(completed)

    def test_orchestrator_graph_compiles(self):
        graph = build_orchestrator_graph()
        assert graph is not None

    def test_api_task_lifecycle(self):
        app = create_app(database_url="sqlite:///:memory:")
        with TestClient(app) as client:
            # Submit
            resp = client.post("/api/v1/tasks", json={
                "repo": "/test/repo",
                "description": "Test task",
                "workflow": "default",
            })
            assert resp.status_code == 201
            task_id = resp.json()["task_id"]

            # Get
            resp = client.get(f"/api/v1/tasks/{task_id}")
            assert resp.status_code == 200
            assert resp.json()["status"] == "queued"

            # List
            resp = client.get("/api/v1/tasks")
            assert resp.status_code == 200
            assert len(resp.json()["tasks"]) >= 1


class TestWorktreeIntegration:
    @pytest.fixture
    def git_repo(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
        return tmp_path

    def test_worktree_create_and_cleanup(self, git_repo):
        mgr = WorktreeManager(git_repo)
        wt = mgr.create(task_id="smoke-001", stage="plan")
        assert wt.exists()
        mgr.cleanup(wt)
        assert not wt.exists()
```

- [ ] **Step 2: Run integration test**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest tests/integration/test_e2e_smoke.py -v`
Expected: 7 passed

- [ ] **Step 3: Run full test suite with coverage**

Run: `cd /Users/buddy/claude-code/agent-fleet && python -m pytest --cov=agent_fleet --cov-report=term-missing -v`
Expected: All tests pass, coverage report generated

- [ ] **Step 4: Run linter**

Run: `cd /Users/buddy/claude-code/agent-fleet && ruff check src/ cli/ tests/`
Expected: No errors (or fix any that appear)

- [ ] **Step 5: Commit**

```bash
git add tests/integration/
git commit -m "test(integration): add end-to-end smoke test validating all layers"
```

---

## Chunk 9: Alembic Migrations

### Task 19: Initialize Alembic

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/001_initial_schema.py`

- [ ] **Step 1: Initialize Alembic**

Run: `cd /Users/buddy/claude-code/agent-fleet && alembic init alembic`

- [ ] **Step 2: Configure alembic/env.py to use our models**

Edit `alembic/env.py` to import `agent_fleet.store.models.Base` and set `target_metadata = Base.metadata`. Set `sqlalchemy.url` from `DATABASE_URL` env var.

- [ ] **Step 3: Generate initial migration**

Run: `cd /Users/buddy/claude-code/agent-fleet && alembic revision --autogenerate -m "initial schema"`

- [ ] **Step 4: Test migration applies cleanly**

Run: `cd /Users/buddy/claude-code/agent-fleet && alembic upgrade head`
Expected: Migration applies successfully

- [ ] **Step 5: Commit**

```bash
git add alembic/ alembic.ini
git commit -m "feat(store): add Alembic migrations for initial schema"
```

---

## Summary

| Chunk | Tasks | What it delivers |
|-------|-------|-----------------|
| 1 | 1-3 | Project scaffolding, CLAUDE.md, exceptions |
| 2 | 4-5 | State store (SQLAlchemy models + repository CRUD) |
| 3 | 6-8 | Agent registry (YAML loader) + workflow config loader + DAG resolution |
| 4 | 9-10 | LiteLLM provider wrapper + code/shell tools with sandboxing |
| 5 | 11 | Git worktree manager for agent isolation |
| 6 | 12-15 | LangGraph orchestrator, state schema, gates, DAG router |
| 7 | 16-17 | FastAPI API + Typer CLI |
| 8 | 18 | Integration smoke test validating all layers |
| 9 | 19 | Alembic database migrations |

**After completing all chunks:** You'll have a fully scaffolded, tested platform where all layers integrate. The next phase will wire the Agent Runner to actually call LLMs and execute agent workflows end-to-end against a real repo.
