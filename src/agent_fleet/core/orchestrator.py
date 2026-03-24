"""LangGraph orchestrator — the core state graph."""

from pathlib import Path
from typing import Literal

import structlog
from langgraph.graph import StateGraph

from agent_fleet.agents.registry import AgentRegistry
from agent_fleet.agents.runner import AgentRunner
from agent_fleet.core.events import log_event
from agent_fleet.core.router import Router
from agent_fleet.core.state import FleetState
from agent_fleet.core.workflow import WorkflowConfig, load_workflow
from agent_fleet.exceptions import WorktreeError
from agent_fleet.models.provider import LLMProvider
from agent_fleet.tools.registry import create_tools
from agent_fleet.workspace.worktree import WorktreeManager

logger = structlog.get_logger()

# Terminal states that end the graph
_TERMINAL_STATES = frozenset({"completed", "error", "interrupted", "cost_limit"})


def should_continue(state: FleetState) -> Literal["route_next", "__end__"]:
    """Decide whether to continue routing or finish the graph."""
    status = state.get("status", "running")
    if status in _TERMINAL_STATES:
        return "__end__"
    return "route_next"


class FleetOrchestrator:
    """Orchestrator with injected dependencies for workflow execution."""

    def __init__(
        self,
        task_id: str = "",
        *,
        workflow: WorkflowConfig | None = None,
        registry: AgentRegistry | None = None,
        workflow_path: Path | None = None,
        agents_dir: Path | None = None,
        repo_path: Path | None = None,
    ) -> None:
        if workflow and registry:
            self._workflow = workflow
            self._registry = registry
        elif workflow_path and agents_dir:
            self._workflow = load_workflow(workflow_path)
            self._registry = AgentRegistry(agents_dir)
        else:
            raise ValueError("Provide either (workflow, registry) or (workflow_path, agents_dir)")
        self._router = Router(self._workflow)
        self._repo_path = repo_path
        self._task_id = task_id

    @property
    def workflow(self) -> WorkflowConfig:
        return self._workflow

    def route_next(self, state: FleetState) -> FleetState:
        """Determine the next stage to execute based on DAG dependencies."""
        completed = set(state.get("completed_stages", []))
        log_event(
            state["task_id"],
            "route",
            {"completed": list(completed)},
        )

        ready = self._router.get_next_stages(completed)

        if not ready:
            logger.info("orchestrator_complete", task_id=state["task_id"])
            return {
                **state,
                "status": "completed",
                "current_stage": None,
                "pending_stages": [],
            }

        # Store all ready stages for parallel execution
        pending = [s.name for s in ready]
        next_stage = pending[0]
        logger.info(
            "orchestrator_route",
            task_id=state["task_id"],
            next_stage=next_stage,
            parallel_stages=pending if len(pending) > 1 else None,
        )
        return {**state, "current_stage": next_stage, "pending_stages": pending}

    def execute_stage(self, state: FleetState) -> FleetState:
        """Execute stage(s). Runs parallel stages concurrently via threading."""
        pending = state.get("pending_stages", [])
        stage_name = state.get("current_stage")

        # Parallel execution: multiple pending stages
        if len(pending) > 1:
            return self._execute_parallel(state, pending)

        if not stage_name:
            return {**state, "status": "error", "error_message": "No current stage"}

        # Single stage execution
        return self._execute_single_stage(state, stage_name)

    def _execute_parallel(self, state: FleetState, stages: list[str]) -> FleetState:
        """Execute multiple stages concurrently using threads."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        task_id = state["task_id"]
        logger.info(
            "parallel_execution_start",
            task_id=task_id,
            stages=stages,
        )

        def run_single(stage_name: str) -> tuple[str, FleetState]:
            """Run a single stage and return (stage_name, result_state)."""
            single_state: FleetState = {
                **state,
                "current_stage": stage_name,
                "pending_stages": [stage_name],
            }
            return stage_name, self._execute_single_stage(single_state, stage_name)

        results: dict[str, FleetState] = {}
        with ThreadPoolExecutor(max_workers=len(stages)) as executor:
            futures = {executor.submit(run_single, s): s for s in stages}
            for future in as_completed(futures):
                stage_name = futures[future]
                try:
                    _, result_state = future.result()
                    results[stage_name] = result_state
                except Exception as e:
                    logger.error(
                        "parallel_stage_failed",
                        task_id=task_id,
                        stage=stage_name,
                        error=str(e),
                    )
                    results[stage_name] = {
                        **state,
                        "status": "error",
                        "error_message": f"Stage {stage_name} failed: {e}",
                    }

        # Merge results: combine stage_outputs and tokens from all stages
        merged_outputs = dict(state.get("stage_outputs", {}))
        total_tokens = state.get("total_tokens", 0)
        worktree_paths: dict[str, str] = {}

        for stage_name, result_state in results.items():
            stage_out = result_state.get("stage_outputs", {})
            if stage_name in stage_out:
                merged_outputs[stage_name] = stage_out[stage_name]
            total_tokens += stage_out.get(stage_name, {}).get("tokens_used", 0)
            if "_worktree_path" in result_state:
                worktree_paths[stage_name] = result_state["_worktree_path"]

        # Check if any stage errored
        for result_state in results.values():
            if result_state.get("status") == "error":
                return {
                    **state,
                    "status": "error",
                    "error_message": result_state.get("error_message"),
                    "stage_outputs": merged_outputs,
                    "total_tokens": total_tokens,
                }

        logger.info(
            "parallel_execution_complete",
            task_id=task_id,
            stages=stages,
            total_tokens=total_tokens,
        )

        return {
            **state,
            "stage_outputs": merged_outputs,
            "total_tokens": total_tokens,
            "_worktree_paths": worktree_paths,
        }

    def _execute_single_stage(self, state: FleetState, stage_name: str) -> FleetState:
        """Execute a single stage (extracted from execute_stage for reuse)."""
        task_id = state["task_id"]
        stage_config = self._workflow.get_stage(stage_name)
        agent_config = self._registry.get(stage_config.agent)
        model = stage_config.model or agent_config.default_model

        log_event(task_id, "execute", {"stage": stage_name, "agent": stage_config.agent})

        # Integrator shortcut
        if stage_config.agent == "integrator":
            return self._execute_integrator(state, stage_name, task_id)

        # Create worktree
        repo_path = Path(state["repo"]) if "repo" in state else self._repo_path
        if not repo_path:
            return {**state, "status": "error", "error_message": "No repo path"}

        worktree_mgr = WorktreeManager(repo_path)
        task_branch = f"fleet/task-{task_id}"

        expected_wt = repo_path / ".fleet-worktrees" / f"fleet-worktree-{task_id}-{stage_name}"
        if expected_wt.exists():
            worktree_mgr.cleanup(expected_wt)

        try:
            worktree_path = worktree_mgr.create(
                task_id=task_id,
                stage=stage_name,
                base_branch=task_branch if self._has_branch(repo_path, task_branch) else None,
            )
        except WorktreeError as e:
            logger.error("worktree_create_failed", task_id=task_id, error=str(e))
            return {**state, "status": "error", "error_message": f"Worktree failed: {e}"}

        # Build task context
        task_context = f"Task: {state.get('description', '')}"
        stage_outputs = state.get("stage_outputs", {})
        if "plan" in stage_outputs and stage_name != "plan":
            plan_output = stage_outputs["plan"].get("output", "")
            task_context += f"\n\n## Architect's Plan\n\n{plan_output}"

        if "review" in stage_outputs and stage_name not in ("plan", "review"):
            review_output = stage_outputs["review"].get("output", "")
            try:
                import json as json_mod

                parsed = json_mod.loads(review_output)
                reasoning = parsed.get("reasoning", review_output)
                score = parsed.get("score", "?")
            except (json_mod.JSONDecodeError, ValueError, TypeError):
                reasoning = review_output
                score = "?"
            task_context += (
                f"\n\n## Reviewer Feedback (score: {score}/100)\n\n"
                f"{reasoning}\n\nPlease address the reviewer's feedback."
            )

        # Run agent
        provider = LLMProvider()
        tools = create_tools(agent_config.tools, worktree_path)
        max_iter = stage_config.max_iterations or 20
        runner = AgentRunner(provider=provider, tools=tools, max_iterations=max_iter)

        run_config = agent_config.model_copy(update={"default_model": model})
        try:
            result = runner.run(run_config, task_context, worktree_path)
        except Exception as e:
            logger.error("agent_run_failed", task_id=task_id, stage=stage_name, error=str(e))
            return {**state, "status": "error", "error_message": f"Agent failed: {e}"}

        new_outputs = {**stage_outputs, stage_name: result.model_dump()}
        total_tokens = state.get("total_tokens", 0) + result.tokens_used

        logger.info(
            "stage_executed",
            task_id=task_id,
            stage=stage_name,
            success=result.success,
            tokens=result.tokens_used,
        )

        return {
            **state,
            "stage_outputs": new_outputs,
            "total_tokens": total_tokens,
            "_worktree_path": str(worktree_path),
        }

    def _execute_integrator(self, state: FleetState, stage_name: str, task_id: str) -> FleetState:
        """Run the integrator stage — generate summary + create PR, no LLM call."""
        from agent_fleet.workspace.pr import detect_provider, generate_pr_body

        stage_outputs = state.get("stage_outputs", {})
        repo_path = Path(state["repo"]) if "repo" in state else self._repo_path

        # Generate PR body
        body = generate_pr_body(
            description=state.get("description", ""),
            workflow_name=state.get("workflow_name", "default"),
            total_tokens=state.get("total_tokens", 0),
            stage_outputs=stage_outputs,
        )

        # Detect provider and create PR, fall back to local on failure
        pr_url: str | None = None
        if repo_path:
            from agent_fleet.workspace.pr import LocalSummaryProvider

            provider = detect_provider(repo_path)
            task_branch = f"fleet/task-{task_id}"
            title = f"Agent Fleet: {state.get('description', 'Task')[:60]}"
            pr_url = provider.create_pr(
                repo_path=repo_path,
                branch=task_branch,
                title=title,
                body=body,
            )
            # Fall back to local summary if PR creation failed
            if pr_url is None and not isinstance(provider, LocalSummaryProvider):
                local = LocalSummaryProvider()
                local.create_pr(repo_path, task_branch, title, body)

        # Store result (no LLM tokens used)
        deliver_output = {
            "success": True,
            "output": body,
            "files_changed": [],
            "tokens_used": 0,
            "iterations": 0,
            "tool_calls": [],
        }
        new_outputs = {**stage_outputs, stage_name: deliver_output}

        logger.info(
            "integrator_executed",
            task_id=task_id,
            pr_url=pr_url,
        )

        return {
            **state,
            "stage_outputs": new_outputs,
            "pr_url": pr_url,
        }

    def _has_branch(self, repo_path: Path, branch: str) -> bool:
        """Check if a branch exists in the repo."""
        import subprocess

        result = subprocess.run(
            ["git", "branch", "--list", branch],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())

    def evaluate_gate(self, state: FleetState) -> FleetState:
        """Evaluate gate(s). For parallel stages, evaluates all gates."""

        pending = state.get("pending_stages", [])

        # For parallel stages, evaluate all gates sequentially
        if len(pending) > 1:
            current_state = state
            for stage in pending:
                current_state = self._evaluate_single_gate(current_state, stage)
                if current_state.get("status") == "error":
                    return current_state
            return current_state

        stage_name = state.get("current_stage")
        if not stage_name:
            return state

        return self._evaluate_single_gate(state, stage_name)

    def _evaluate_single_gate(self, state: FleetState, stage_name: str) -> FleetState:
        """Evaluate a single stage's gate."""
        import subprocess as sp

        task_id = state["task_id"]
        stage_config = self._workflow.get_stage(stage_name)
        gate = stage_config.gate
        worktree_path = state.get("_worktree_path", "")

        log_event(task_id, "gate", {"stage": stage_name, "gate_type": gate.type})

        # Evaluate gate
        passed = False
        route_to_stage: str | None = None
        if gate.type == "approval":
            # Auto-approve for PoC
            passed = True
            logger.info("gate_auto_approved", task_id=task_id, stage=stage_name)
        elif gate.type == "automated":
            # Run checks
            check_results: dict[str, bool] = {}
            for check in gate.checks:
                if check == "tests_pass" and worktree_path:
                    result = sp.run(
                        ["python", "-m", "pytest", "--tb=short", "-q"],
                        cwd=worktree_path,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    check_results[check] = result.returncode == 0
                    logger.info(
                        "gate_check",
                        task_id=task_id,
                        check=check,
                        passed=result.returncode == 0,
                        output=result.stdout[-500:] if result.stdout else "",
                    )
                else:
                    check_results[check] = True  # Unknown checks pass by default
            passed = all(check_results.values())
        elif gate.type == "score":
            passed, route_to_stage = self._evaluate_score_gate(state, stage_name, gate)

        # Handle result
        completed = list(state.get("completed_stages", []))
        retry_counts = dict(state.get("retry_counts", {}))

        if passed:
            completed.append(stage_name)
            logger.info("gate_passed", task_id=task_id, stage=stage_name)
            return {
                **state,
                "completed_stages": completed,
                "retry_counts": retry_counts,
            }

        # Gate failed
        retry_counts[stage_name] = retry_counts.get(stage_name, 0) + 1
        max_retries = gate.max_retries or 2

        if retry_counts[stage_name] > max_retries:
            logger.error(
                "gate_max_retries",
                task_id=task_id,
                stage=stage_name,
                retries=retry_counts[stage_name],
            )
            return {
                **state,
                "status": "error",
                "error_message": f"Gate failed at {stage_name} after {max_retries} retries",
                "retry_counts": retry_counts,
            }

        # For score gate: route back to the specified stage
        if gate.type == "score" and route_to_stage and route_to_stage in completed:
            completed.remove(route_to_stage)
            logger.info(
                "gate_route_back",
                task_id=task_id,
                from_stage=stage_name,
                to_stage=route_to_stage,
            )

        logger.warning(
            "gate_failed_retry",
            task_id=task_id,
            stage=stage_name,
            retry=retry_counts[stage_name],
        )
        return {**state, "completed_stages": completed, "retry_counts": retry_counts}

    def _evaluate_score_gate(
        self,
        state: FleetState,
        stage_name: str,
        gate: object,
    ) -> tuple[bool, str | None]:
        """Parse reviewer JSON output and evaluate score gate.

        Returns (passed, route_to_stage).
        """
        import json as json_mod

        stage_outputs = state.get("stage_outputs", {})
        output_str = stage_outputs.get(stage_name, {}).get("output", "")

        # Parse JSON from reviewer output — try raw first, then extract from markdown
        score = 0
        route_to_stage: str | None = None
        parsed = None
        try:
            parsed = json_mod.loads(output_str)
        except (json_mod.JSONDecodeError, ValueError, TypeError):
            # Try extracting JSON from markdown code block
            import re

            json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", output_str, re.DOTALL)
            if json_match:
                try:
                    parsed = json_mod.loads(json_match.group(1).strip())
                except (json_mod.JSONDecodeError, ValueError, TypeError):
                    pass
            # Try finding first { ... } block
            if parsed is None:
                brace_match = re.search(r"\{.*\}", output_str, re.DOTALL)
                if brace_match:
                    try:
                        parsed = json_mod.loads(brace_match.group(0))
                    except (json_mod.JSONDecodeError, ValueError, TypeError):
                        pass

        if parsed and isinstance(parsed, dict):
            score = int(parsed.get("score", 0))
            route_to_stage = parsed.get("route_to")
        else:
            logger.warning(
                "score_gate_parse_failed",
                task_id=state["task_id"],
                stage=stage_name,
                output_preview=output_str[:200],
            )

        min_score = getattr(gate, "min_score", 0) or 0
        passed = score >= min_score

        logger.info(
            "score_gate_evaluated",
            task_id=state["task_id"],
            stage=stage_name,
            score=score,
            min_score=min_score,
            passed=passed,
        )

        # Fallback route_to: gate config route_target, then first depends_on
        if not passed and not route_to_stage:
            route_to_stage = getattr(gate, "route_target", None)
            if not route_to_stage:
                stage_config = self._workflow.get_stage(stage_name)
                if stage_config.depends_on:
                    route_to_stage = stage_config.depends_on[0]

        return passed, route_to_stage

    def build_graph(self) -> StateGraph:
        """Build and compile the LangGraph state graph."""
        graph = StateGraph(FleetState)

        graph.add_node("route_next", self.route_next)
        graph.add_node("execute_stage", self.execute_stage)
        graph.add_node("evaluate_gate", self.evaluate_gate)

        graph.set_entry_point("route_next")
        # route_next may set status="completed" — skip execution if so
        graph.add_conditional_edges(
            "route_next",
            should_continue,
            {
                "route_next": "execute_stage",  # continue → execute
                "__end__": "__end__",  # terminal → stop
            },
        )
        graph.add_edge("execute_stage", "evaluate_gate")
        graph.add_conditional_edges(
            "evaluate_gate",
            should_continue,
            {
                "route_next": "route_next",
                "__end__": "__end__",
            },
        )

        return graph.compile()


# Backward-compatible standalone functions for existing tests
def route_next(state: FleetState) -> FleetState:
    """Stub route_next for backward compatibility."""
    log_event(
        state["task_id"],
        "route",
        {"completed": state.get("completed_stages", [])},
    )
    return state


def execute_stage(state: FleetState) -> FleetState:
    """Stub execute_stage for backward compatibility."""
    stage = state.get("current_stage")
    log_event(state["task_id"], "execute", {"stage": stage})
    return state


def evaluate_gate(state: FleetState) -> FleetState:
    """Stub evaluate_gate for backward compatibility."""
    stage = state.get("current_stage")
    log_event(state["task_id"], "gate", {"stage": stage})
    return state


def build_orchestrator_graph() -> StateGraph:
    """Build orchestrator graph with stub functions (backward compatible)."""
    graph = StateGraph(FleetState)

    graph.add_node("route_next", route_next)
    graph.add_node("execute_stage", execute_stage)
    graph.add_node("evaluate_gate", evaluate_gate)

    graph.set_entry_point("route_next")
    graph.add_edge("route_next", "execute_stage")
    graph.add_edge("execute_stage", "evaluate_gate")
    graph.add_conditional_edges("evaluate_gate", should_continue)

    return graph.compile()
