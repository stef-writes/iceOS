from __future__ import annotations

from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

class CircuitBreaker:  # noqa: D101 – placeholder stub
    def __init__(self, failure_threshold: int = 3):
        self.failure_threshold = failure_threshold

    def protect(self, func: Callable[P, R]) -> Callable[P, R]:
        return func


def circuit_breaker(func: Callable[P, R]) -> Callable[P, R]:  # noqa: D401
    """Decorator alias matching the previous API; no-op for now."""

    return func 