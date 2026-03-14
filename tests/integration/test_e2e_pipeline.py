"""E2E integration test — two-stage pipeline with mocked LLM."""

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_fleet.core.orchestrator import FleetOrchestrator
from agent_fleet.core.state import FleetState
from agent_fleet.models.provider import LLMResponse

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
TEST_REPO_SRC = Path(__file__).parent.parent / "fixtures" / "test-repo"


@pytest.fixture
def test_repo(tmp_path: Path) -> Path:
    """Copy the test-repo fixture to a temp dir and init git."""
    repo = tmp_path / "test-repo"
    shutil.copytree(TEST_REPO_SRC, repo)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t.com"],
        cwd=repo, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "T"],
        cwd=repo, capture_output=True, check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo, capture_output=True, check=True,
    )
    # Create task branch
    subprocess.run(
        ["git", "branch", "fleet/task-e2e"],
        cwd=repo, capture_output=True, check=True,
    )
    return repo


def _make_llm_response(content: str, tokens: int = 50) -> LLMResponse:
    """Create a simple text LLMResponse (no tool calls)."""
    return LLMResponse(
        content=content,
        model="mock/model",
        tokens_used=tokens,
        tool_calls=None,
        raw_message={"role": "assistant", "content": content},
    )


def _make_tool_call_response(
    call_id: str, tool_name: str, args: dict, tokens: int = 30
) -> LLMResponse:
    """Create an LLMResponse with a tool call."""
    args_str = json.dumps(args)
    return LLMResponse(
        content="",
        model="mock/model",
        tokens_used=tokens,
        tool_calls=[{
            "id": call_id,
            "function": {"name": tool_name, "arguments": args_str},
        }],
        raw_message={
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {"name": tool_name, "arguments": args_str},
            }],
        },
    )


class TestTwoStagePipeline:
    @patch("agent_fleet.core.orchestrator.LLMProvider")
    def test_full_pipeline_mocked(
        self,
        mock_provider_cls: MagicMock,
        test_repo: Path,
    ) -> None:
        """Full two-stage pipeline with mocked LLM responses."""
        mock_provider = MagicMock()

        # Plan stage: architect reads calculator.py then produces plan
        # Backend stage: dev reads file, writes multiply, writes test, produces output
        call_count = 0

        def mock_complete(**kwargs: object) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            messages = kwargs.get("messages", [])

            # Detect which stage by system prompt content
            system_msg = messages[0]["content"] if messages else ""

            if "architect" in system_msg.lower():
                # Architect: just return a plan (no tool calls)
                return _make_llm_response(
                    "## Plan\n\n### Files to Change\n"
                    "- src/calculator.py: add multiply(a, b)\n"
                    "- tests/test_calculator.py: add test_multiply\n\n"
                    "### Approach\n"
                    "Add multiply function and tests.",
                    tokens=200,
                )
            else:
                # Backend dev: tool call sequence
                # Figure out which step we're on by counting tool messages
                tool_msgs = [m for m in messages if m.get("role") == "tool"]

                if len(tool_msgs) == 0:
                    # Step 1: read calculator.py
                    return _make_tool_call_response(
                        "c1", "read_file", {"path": "src/calculator.py"}
                    )
                elif len(tool_msgs) == 1:
                    # Step 2: write multiply to calculator.py
                    new_code = (
                        '"""Simple calculator module."""\n\n\n'
                        "def add(a: float, b: float) -> float:\n"
                        '    """Add two numbers."""\n'
                        "    return a + b\n\n\n"
                        "def subtract(a: float, b: float) -> float:\n"
                        '    """Subtract b from a."""\n'
                        "    return a - b\n\n\n"
                        "def multiply(a: float, b: float) -> float:\n"
                        '    """Multiply two numbers."""\n'
                        "    return a * b\n"
                    )
                    return _make_tool_call_response(
                        "c2", "write_file",
                        {"path": "src/calculator.py", "content": new_code},
                    )
                elif len(tool_msgs) == 2:
                    # Step 3: write test
                    test_code = (
                        '"""Tests for calculator module."""\n\n'
                        "from src.calculator import add, subtract, multiply\n\n\n"
                        "def test_add() -> None:\n"
                        "    assert add(2, 3) == 5\n"
                        "    assert add(-1, 1) == 0\n"
                        "    assert add(0, 0) == 0\n\n\n"
                        "def test_subtract() -> None:\n"
                        "    assert subtract(5, 3) == 2\n"
                        "    assert subtract(0, 5) == -5\n"
                        "    assert subtract(10, 10) == 0\n\n\n"
                        "def test_multiply() -> None:\n"
                        "    assert multiply(3, 4) == 12\n"
                        "    assert multiply(-2, 5) == -10\n"
                        "    assert multiply(0, 100) == 0\n"
                    )
                    return _make_tool_call_response(
                        "c3", "write_file",
                        {"path": "tests/test_calculator.py", "content": test_code},
                    )
                else:
                    # Step 4: done
                    return _make_llm_response(
                        "Added multiply function and tests.", tokens=50
                    )

        mock_provider.complete.side_effect = mock_complete
        mock_provider_cls.return_value = mock_provider

        # Build orchestrator
        orch = FleetOrchestrator(
            workflow_path=CONFIG_DIR / "workflows" / "two-stage.yaml",
            agents_dir=CONFIG_DIR / "agents",
            repo_path=test_repo,
        )

        state: FleetState = {
            "task_id": "e2e",
            "repo": str(test_repo),
            "description": "Add a multiply(a, b) function to the calculator",
            "workflow_name": "two-stage",
            "status": "running",
            "current_stage": None,
            "completed_stages": [],
            "retry_counts": {},
            "stage_outputs": {},
            "stage_errors": {},
            "total_tokens": 0,
            "total_cost_usd": 0.0,
        }

        graph = orch.build_graph()
        final = graph.invoke(state)

        # Verify pipeline completed
        assert final["status"] == "completed"
        assert "plan" in final["completed_stages"]
        assert "backend" in final["completed_stages"]
        assert final["total_tokens"] > 0

        # Verify architect produced a plan
        assert "plan" in final["stage_outputs"]
        assert "multiply" in final["stage_outputs"]["plan"]["output"].lower()
