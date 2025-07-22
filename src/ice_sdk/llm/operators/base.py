from __future__ import annotations

from typing import Any, Callable, ParamSpec, TypeVar

from pydantic import BaseModel

from ice_sdk.processors.base import Processor
from ice_sdk.models.config import LLMConfig, ModelProvider  # NEW – align with LLMService expectations

from functools import wraps

# ---------------------------------------------------------------------------
# Optional cost-tracking decorator – gracefully degrade when unavailable ----

P = ParamSpec("P")
R = TypeVar("R")


# Robust no-op decorator that supports optional keyword/positional arguments
def _noop_decorator(*d_args: Any, **d_kwargs: Any):  # noqa: D401 – flexible shim
    """Return *func* unchanged regardless of how the decorator is invoked.

    Handles both parameterless ``@decorator`` and parametrised ``@decorator(x=1)``
    invocations so that call-sites remain syntactically valid even when the
    real implementation is unavailable at import-time (e.g., during unit
    tests without the optional *cost* module).
    """

    if d_args and callable(d_args[0]) and len(d_args) == 1 and not d_kwargs:
        # Used as plain @decorator -----------------------------------------
        func = d_args[0]
        return func  # type: ignore[return-value]

    # Used as @decorator(key=value) – return wrapper factory ----------------
    def _inner(func: Callable[P, R]) -> Callable[P, R]:  # noqa: D401
        @wraps(func)
        def _wrapped(*args: P.args, **kwargs: P.kwargs):  # type: ignore[misc]
            return func(*args, **kwargs)

        return _wrapped  # type: ignore[return-value]

    return _inner


try:
    from ice_sdk.utils.cost import track_cost  # type: ignore  # pragma: no cover
except Exception:  # pragma: no cover – util may not exist yet
    track_cost = _noop_decorator  # type: ignore[assignment]


def operator(func: Callable[P, R]) -> Callable[P, R]:
    """Marker decorator for LLM operator functions (currently a no-op)."""
    return func


class LLMOperatorConfig(BaseModel):
    provider: ModelProvider = ModelProvider.OPENAI  # NEW – provider field with default
    model: str = "gpt-4o"
    max_tokens: int = 2000
    temperature: float = 0.7


class LLMOperator(Processor[LLMOperatorConfig]):  # Inherits validation
    """Base LLM interaction unit"""

    config: LLMOperatorConfig  # explicit for static checkers

    # Most LLM operators don't use explicit JSONSchema for IO at this layer; they
    # validate through their Pydantic Input/Output models instead.  Override the
    # *Processor.validate* hook so registration doesn't fail on missing schemas.

    def validate(self) -> bool:  # noqa: D401 – override
        return True

    @track_cost(category="llm_operator")
    async def generate(self, prompt: str) -> str:
        llm_svc: Any = getattr(self, "llm_service", None)
        if llm_svc is None:
            raise RuntimeError("llm_service not configured on LLMOperator instance")

        # Build LLMConfig dynamically from self.config -----------------------
        llm_cfg = LLMConfig(  # type: ignore[call-arg]
            provider=self.config.provider.value if hasattr(self.config.provider, "value") else self.config.provider,
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        text, _usage, err = await llm_svc.generate(llm_cfg, prompt)
        if err:
            raise RuntimeError(err)
        return text
