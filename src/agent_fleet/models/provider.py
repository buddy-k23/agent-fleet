"""LiteLLM wrapper for unified model access."""

import structlog
from litellm import completion as litellm_completion
from pydantic import BaseModel

from agent_fleet.exceptions import LLMProviderError

logger = structlog.get_logger()


class LLMResponse(BaseModel):
    """Structured response from an LLM call."""

    content: str
    model: str
    tokens_used: int
    cost_usd: float = 0.0


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
        """Call an LLM via LiteLLM and return a structured response."""
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

            logger.info("llm_completion", model=model, tokens=tokens)

            return response

        except LLMProviderError:
            raise
        except Exception as e:
            logger.error("llm_completion_failed", model=model, error=str(e))
            raise LLMProviderError(f"LLM call failed: {e}") from e

    def within_budget(self, max_tokens: int) -> bool:
        """Check if total token usage is within budget."""
        return self.total_tokens_used < max_tokens
