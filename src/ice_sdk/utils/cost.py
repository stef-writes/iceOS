"""Light-weight cost-tracking utilities local to *ice_sdk*.

The *LLMOperator* modules depend on a ``track_cost`` decorator but we do not
require full budget enforcement here.  Providing a statically-typed no-op
implementation ensures

1.  mypy treats decorated functions as fully typed (avoids "untyped decorator")
2.  Runtime keeps minimal overhead until a future instrumentation layer lands.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def track_cost(
    *, category: str | None = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:  # noqa: D401
    """Return a decorator that transparently forwards its wrapped callable.

    Parameters
    ----------
    category: str | None, optional
        Logical cost category (ignored by this stub).
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore[misc]
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
