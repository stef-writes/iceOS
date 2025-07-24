"""Performance helpers for orchestrator (dependency-free)."""

from __future__ import annotations

import asyncio
from typing import Any

__all__ = ["estimate_complexity", "WeightedSemaphore"]

def estimate_complexity(node_cfg: Any) -> int:  # – generic for now
    # Avoid cross-layer imports – infer complexity heuristically -------------
    cls_name = getattr(getattr(node_cfg, "__class__", None), "__name__", "")
    if cls_name == "LLMOperatorConfig":
        return 2
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
