from __future__ import annotations

from types import TracebackType
from typing import Callable, Optional, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class CircuitBreaker:  # noqa: D101 – placeholder stub
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        # Runtime behaviour is a no-op for the demo – store values for later.
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    # ------------------------------------------------------------------
    # Async context-manager interface so ``async with CircuitBreaker()``
    # compiles under strict typing.
    # ------------------------------------------------------------------

    # Type hints ---------------------------------------------------------------

    async def __aenter__(self) -> "CircuitBreaker":  # noqa: D401 – context helper
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> bool:  # noqa: D401 – ctx helper
        # Always propagate exceptions – the outer retry/backoff logic handles
        # error counting.  Returning *False* signals normal exception flow.
        return False

    def protect(self, func: Callable[P, R]) -> Callable[P, R]:  # noqa: D401
        """Pass-through decorator retained for API compatibility."""
        return func


# ---------------------------------------------------------------------------
# Helper decorator alias
# ---------------------------------------------------------------------------


def circuit_breaker(func: Callable[P, R]) -> Callable[P, R]:  # noqa: D401
    """Decorator alias matching the previous API; no-op for now."""

    return func


class NodeCircuitBreaker(CircuitBreaker):
    """Per-node breaker placeholder – identical to base for now."""

    def __init__(self, node_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_id = node_id
