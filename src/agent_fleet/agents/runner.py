"""AgentRunner — ReAct tool loop for agent execution."""

import json
import subprocess
from pathlib import Path
from typing import Any

import structlog

from agent_fleet.agents.base import AgentConfig
from agent_fleet.agents.result import AgentResult
from agent_fleet.models.provider import LLMProvider
from agent_fleet.tools.base import BaseTool
from agent_fleet.tools.registry import tool_to_litellm_schema

logger = structlog.get_logger()


class AgentRunner:
    """Executes an agent using a ReAct-style tool-use loop.

    The runner calls the LLM with tool schemas. When the LLM returns
    tool calls, it executes them and feeds results back. When the LLM
    returns text with no tool calls, that's the final answer.
    """

    def __init__(
        self,
        provider: LLMProvider,
        tools: list[BaseTool],
        max_iterations: int = 20,
    ) -> None:
        self._provider = provider
        self._tools = {tool.name: tool for tool in tools}
        self._tool_schemas = [tool_to_litellm_schema(t) for t in tools]
        self._max_iterations = max_iterations

    def run(
        self,
        agent_config: AgentConfig,
        task_context: str,
        worktree_path: Path,
    ) -> AgentResult:
        """Execute the agent's ReAct loop."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": agent_config.system_prompt},
            {"role": "user", "content": task_context},
        ]

        total_tokens = 0
        all_tool_calls: list[dict] = []

        for iteration in range(1, self._max_iterations + 1):
            logger.info(
                "agent_iteration",
                agent=agent_config.name,
                iteration=iteration,
            )

            response = self._provider.complete(
                model=agent_config.default_model,
                messages=messages,
                tools=self._tool_schemas if self._tool_schemas else None,
            )
            total_tokens += response.tokens_used

            # No tool calls — final answer
            if not response.tool_calls:
                return AgentResult(
                    success=True,
                    output=response.content,
                    files_changed=self._get_files_changed(worktree_path),
                    tokens_used=total_tokens,
                    iterations=iteration,
                    tool_calls=all_tool_calls,
                )

            # Append assistant message with tool calls to history
            if response.raw_message:
                messages.append(response.raw_message)

            # Execute each tool call
            for tc in response.tool_calls:
                tool_call_id = tc["id"]
                func_name = tc["function"]["name"]
                func_args_str = tc["function"]["arguments"]

                # Parse arguments
                try:
                    func_args = json.loads(func_args_str)
                except json.JSONDecodeError:
                    tool_result = "Invalid JSON arguments. Please retry with valid JSON."
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": tool_result,
                        }
                    )
                    continue

                # Look up and execute tool
                tool = self._tools.get(func_name)
                if tool is None:
                    available = ", ".join(sorted(self._tools.keys()))
                    tool_result = f"Tool '{func_name}' not found. Available tools: {available}"
                else:
                    result = tool.execute(func_args)
                    tool_result = json.dumps(result)
                    all_tool_calls.append(
                        {
                            "tool": func_name,
                            "args": func_args,
                            "result": result,
                        }
                    )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": tool_result,
                    }
                )

        # Max iterations reached
        logger.warning(
            "agent_max_iterations",
            agent=agent_config.name,
            max_iterations=self._max_iterations,
        )
        return AgentResult(
            success=False,
            output="Max iterations reached",
            files_changed=self._get_files_changed(worktree_path),
            tokens_used=total_tokens,
            iterations=self._max_iterations,
            tool_calls=all_tool_calls,
        )

    def _get_files_changed(self, worktree_path: Path) -> list[str]:
        """Get list of modified and new files in the worktree."""
        changed: list[str] = []

        # Modified files
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            changed.extend(f for f in result.stdout.strip().splitlines() if f)

        # New untracked files
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            changed.extend(f for f in result.stdout.strip().splitlines() if f)

        return changed
