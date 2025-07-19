from __future__ import annotations

from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from ice_sdk.processors.base import Processor

# ---------------------------------------------------------------------------
# Optional cost-tracking decorator – gracefully degrade when unavailable ----

T_Call = TypeVar("T_Call", bound=Callable[..., Any])


def _noop_decorator(func: T_Call) -> T_Call:  # noqa: D401 – pass‐through
    return func


try:
    from ice_sdk.utils.cost import track_cost  # type: ignore  # pragma: no cover
except Exception:  # pragma: no cover – util may not exist yet
    track_cost = _noop_decorator  # type: ignore[arg-type]

F = TypeVar("F", bound=Callable[..., Any])


def operator(func: F) -> F:  # noqa: D401
    """Marker decorator for LLM operator functions (currently a no-op)."""
    return func  # type: ignore[misc]


class LLMOperatorConfig(BaseModel):
    model: str = "gpt-4-1106-preview"
    max_tokens: int = 2000
    temperature: float = 0.7


class LLMOperator(Processor[LLMOperatorConfig]):  # Inherits validation
    """Base LLM interaction unit"""

    config: LLMOperatorConfig  # explicit for static checkers

    @track_cost(category="llm_operator")
    async def generate(self, prompt: str) -> str:  # noqa: D401
        # *llm_service* is provided by concrete subclasses / DI; treat as Any
        llm_svc: Any = getattr(self, "llm_service", None)
        if llm_svc is None:
            raise RuntimeError("llm_service not configured on LLMOperator instance")

        return await llm_svc.generate(  # type: ignore[no-any-return]
            prompt=prompt,
            model=self.config.model,
            max_tokens=self.config.max_tokens,
        )
