"""Performance helpers for orchestrator.

Utilities deliberately kept free of external dependencies so they work in any
execution environment.
"""

from __future__ import annotations

import asyncio
from typing import Any

# ---------------------------------------------------------------------------
# Complexity estimation ------------------------------------------------------
# ---------------------------------------------------------------------------


def estimate_complexity(node_cfg: Any) -> int:  # noqa: ANN401 – generic for now
    """Return an *int* weight representing relative resource usage.

    Heuristic rules (can be tuned):
        * AI nodes            → 2
        * Tool nodes          → 1
        * Condition / misc    → 1
    """

    try:
        from ice_sdk.models.node_models import AiNodeConfig

        if isinstance(node_cfg, AiNodeConfig):
            return 2  # LLM calls are heavier
    except Exception:  # pragma: no cover – avoid hard dep cycles
        pass

    return 1


# ---------------------------------------------------------------------------
# Weighted semaphore ---------------------------------------------------------
# ---------------------------------------------------------------------------


class WeightedSemaphore:
    """Async context-manager that acquires *weight* slots from *sem*.

    Example::

        sem = asyncio.Semaphore(5)
        async with WeightedSemaphore(sem, weight=3):
            ...
    """

    def __init__(self, sem: asyncio.Semaphore, weight: int = 1):
        if weight < 1:
            raise ValueError("weight must be ≥1")
        self._sem = sem
        self._weight = weight

    async def __aenter__(self):  # noqa: D401
        for _ in range(self._weight):
            await self._sem.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
        for _ in range(self._weight):
            self._sem.release()
        # Do not suppress exceptions
        return False
