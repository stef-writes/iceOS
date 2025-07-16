"""Performance helpers for orchestrator (dependency-free)."""

from __future__ import annotations

import asyncio
from typing import Any

__all__ = ["estimate_complexity", "WeightedSemaphore"]


def estimate_complexity(node_cfg: Any) -> int:  # noqa: ANN401 – generic for now
    try:
        from ice_sdk.models.node_models import AiNodeConfig  # noqa: WPS433 – optional

        if isinstance(node_cfg, AiNodeConfig):
            return 2
    except Exception:
        pass
    return 1


class WeightedSemaphore:
    """Async context-manager that acquires *weight* slots from *sem*."""

    def __init__(self, sem: asyncio.Semaphore, weight: int = 1):
        if weight < 1:
            raise ValueError("weight must be ≥1")
        self._sem = sem
        self._weight = weight

    async def __aenter__(self):
        for _ in range(self._weight):
            await self._sem.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        for _ in range(self._weight):
            self._sem.release()
        return False
