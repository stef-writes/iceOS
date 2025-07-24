from __future__ import annotations

"""Lightweight async retry helper used by NetworkService.

Avoids pulling an external dependency while providing deterministic behaviour
for unit tests.
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

def async_retry(
    *, attempts: int | None = None, max_attempts: int | None = None, delay: float = 0.1
) -> Callable[[Callable[..., Awaitable[_T]]], Callable[..., Awaitable[_T]]]:
    """Decorate an **async** function with simple retry logic.

    Parameters
    ----------
    attempts : int
        How many attempts in total (default 3).
    delay : float
        Fixed delay between attempts in seconds.
    """

    effective_attempts = attempts or max_attempts or 3

    def _decorator(func: Callable[..., Awaitable[_T]]) -> Callable[..., Awaitable[_T]]:
        @wraps(func)
        async def _wrapper(*args: Any, **kwargs: Any) -> _T:  # type: ignore[override]
            last_exc: Exception | None = None
            for i in range(effective_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:  # pragma: no cover – intentional broad catch
                    last_exc = exc
                    logger.debug(
                        "Retry %s/%s for %s due to %s",
                        i + 1,
                        effective_attempts,
                        func.__name__,
                        exc,
                    )
                    await asyncio.sleep(delay)
            # If reached here all retries exhausted
            assert last_exc is not None
            raise last_exc

        return _wrapper

    return _decorator
