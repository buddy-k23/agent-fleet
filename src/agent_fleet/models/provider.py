"""LiteLLM wrapper for unified model access."""

import time

import structlog
from litellm import completion as litellm_completion
from litellm.exceptions import RateLimitError
from pydantic import BaseModel

from agent_fleet.exceptions import LLMProviderError

logger = structlog.get_logger()

# Retry config for rate limits
_RATE_LIMIT_MAX_RETRIES = 3
_RATE_LIMIT_BACKOFF = [5, 15, 30]  # seconds


class LLMResponse(BaseModel):
    """Structured response from an LLM call."""

    content: str
    model: str
    tokens_used: int
    cost_usd: float = 0.0
    tool_calls: list[dict] | None = None
    raw_message: dict | None = None


class LLMProvider:
    """Unified LLM provider using LiteLLM. Tracks token usage across calls."""

    def __init__(self) -> None:
        self.total_tokens_used: int = 0
        self.total_cost_usd: float = 0.0

    def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Call an LLM via LiteLLM with rate limit retry."""
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools

        last_error: Exception | None = None
        for attempt in range(_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                return self._do_complete(model, kwargs)
            except RateLimitError as e:
                last_error = e
                if attempt < _RATE_LIMIT_MAX_RETRIES:
                    wait = _RATE_LIMIT_BACKOFF[attempt]
                    logger.warning(
                        "rate_limit_retry",
                        model=model,
                        attempt=attempt + 1,
                        wait_seconds=wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "rate_limit_exhausted",
                        model=model,
                        retries=_RATE_LIMIT_MAX_RETRIES,
                    )
            except LLMProviderError:
                raise
            except Exception as e:
                logger.error("llm_completion_failed", model=model, error=str(e))
                raise LLMProviderError(f"LLM call failed: {e}") from e

        raise LLMProviderError(
            f"Rate limit exceeded after {_RATE_LIMIT_MAX_RETRIES} retries: {last_error}"
        )

    def _do_complete(self, model: str, kwargs: dict) -> LLMResponse:
        """Execute a single LLM completion call."""
        result = litellm_completion(**kwargs)

        tokens = result.usage.total_tokens if result.usage else 0
        self.total_tokens_used += tokens

        message = result.choices[0].message
        content = message.content or ""

        # Extract tool calls if present
        raw_tool_calls = getattr(message, "tool_calls", None)
        tool_calls_data: list[dict] | None = None
        if raw_tool_calls and isinstance(raw_tool_calls, list):
            tool_calls_data = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in raw_tool_calls
            ]

        # Get raw message for conversation history
        raw_message: dict | None = None
        try:
            dumped = message.model_dump()
            if isinstance(dumped, dict):
                raw_message = dumped
        except (AttributeError, TypeError):
            pass

        response = LLMResponse(
            content=content,
            model=result.model or model,
            tokens_used=tokens,
            tool_calls=tool_calls_data,
            raw_message=raw_message,
        )

        logger.info("llm_completion", model=model, tokens=tokens)
        return response

    def within_budget(self, max_tokens: int) -> bool:
        """Check if total token usage is within budget."""
        return self.total_tokens_used < max_tokens
