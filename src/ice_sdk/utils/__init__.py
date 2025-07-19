"""Utility helpers (logging, error handling, etc.) shared by ice_* packages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, ParamSpec, TypeVar

from ice_core.utils.logging import logger, setup_logger  # noqa: F401 re-export
from ice_core.utils.meta import public  # noqa: F401 re-export
from ice_core.utils.security import sanitize_path  # noqa: F401
from ice_core.utils.text import TextProcessor  # noqa: F401 re-export
from ice_sdk.utils.errors import (  # noqa: F401 re-export
    APIError,
    add_exception_handlers,
)

if TYPE_CHECKING:
    from ice_core.utils.coercion import coerce_types  # noqa: F401
    from ice_sdk.runtime.token_counter import TokenCounter  # noqa: F401

__all__ = [
    "logger",
    "setup_logger",
    "APIError",
    "add_exception_handlers",
    "TokenCounter",
    "coerce_types",
    "sanitize_path",
    "TextProcessor",
]

__all__.append("public")

# Public re-export for backwards compatibility ---------------------------------
from .hashing import stable_hash  # noqa: E402 F401

__all__.append("stable_hash")

# Lazy imports to avoid unnecessary dependency loading on lightweight clients.

P = ParamSpec("P")
R = TypeVar("R")


def circuit_breaker(func: Callable[P, R]) -> Callable[P, R]:  # noqa: D401 – stub
    """Lightweight no-op circuit breaker decorator.

    Provides the attribute *protect* expected by SkillBase.  In production we
    will replace this with a proper implementation or reuse the one from
    providers.  For now it simply returns the function unchanged.
    """

    return func


class CircuitBreaker:  # noqa: D101 – placeholder
    def __init__(self, failure_threshold: int = 3):
        self.failure_threshold = failure_threshold

    def protect(self, func: Callable[P, R]) -> Callable[P, R]:  # noqa: D401
        return func
