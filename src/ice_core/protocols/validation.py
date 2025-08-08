"""Validation helpers for protocol compliance.

This module provides :pyfunc:`validated_protocol` – a decorator that can be
applied to *both* classes **and** callables to guarantee they implement the
expected runtime protocol.

The decorator serves two use-cases:

1. **Agent / Node classes** – enforcement is identical to the existing
   :pyfunc:`enforce_protocol` helper, but re-exported under a clearer name that
   reflects the hardening plan terminology.
2. **Executor callables** – an extra validation branch that asserts the target
   is an ``async`` function with the canonical ``(workflow, cfg, ctx)``
   signature that returns a :class:`ice_core.models.NodeExecutionResult`.

Having a single decorator makes it obvious (and testable) that *every* runtime
component entering the orchestrator conforms to a strict, audited contract.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Protocol, TypeVar, runtime_checkable

from ice_core.models.node_models import NodeExecutionResult  # Local import, same layer

from . import IAgent, IExecutor, enforce_protocol  # Re-use existing helpers

F = TypeVar("F")

# ---------------------------------------------------------------------------
# Signature expectations for executor callables
# ---------------------------------------------------------------------------

_EXPECTED_PARAM_COUNT = 3  # workflow, cfg, ctx


def _validate_executor_callable(fn: Any) -> None:
    """Raise ``TypeError`` if *fn* is not a compliant executor coroutine."""

    if not inspect.iscoroutinefunction(fn):
        raise TypeError(
            f"Executor {fn.__qualname__} must be an *async* coroutine function"
        )

    sig = inspect.signature(fn)
    if len(sig.parameters) < _EXPECTED_PARAM_COUNT:
        raise TypeError(
            f"Executor {fn.__qualname__} must accept at least the parameters "
            "(workflow, cfg, ctx) in that order"
        )

    # Basic return-type check – we tolerate absent annotations to avoid
    # over-restricting existing code but validate when present.
    return_type = sig.return_annotation
    if (
        return_type is not inspect.Signature.empty
        and return_type is not NodeExecutionResult
    ):
        raise TypeError(
            f"Executor {fn.__qualname__} must return ice_core.models.NodeExecutionResult"
        )


# ---------------------------------------------------------------------------
# Public decorator
# ---------------------------------------------------------------------------


@runtime_checkable
class _Protocolish(Protocol):
    """Anything that can be treated as a runtime-checkable typing Protocol."""

    ...


def validated_protocol(proto: str | type[_Protocolish]) -> Callable[[F], F]:
    """Return a decorator that enforces *proto* compliance at import time.

    The *proto* argument can be either a string identifier ("agent" / "executor")
    or a concrete ``typing.Protocol`` subclass.
    """

    # Resolve shorthand strings – keeps call-sites concise.
    mapping: dict[str, type[Any]] = {
        "agent": IAgent,
        "executor": IExecutor,
    }

    protocol: type[_Protocolish]
    if isinstance(proto, str):
        try:
            protocol = mapping[proto]
        except KeyError as err:
            from ice_core.exceptions import ValidationError

            raise ValidationError(
                f"Unknown protocol alias '{proto}'. Valid options: {sorted(mapping)}"
            ) from err
    else:
        protocol = proto  # type: ignore[assignment]

    def decorator(target: F) -> F:  # noqa: D401 – decorator
        # Branch based on whether we decorate a class or a callable.
        if inspect.isclass(target):
            # Delegate to existing utility for class validation.
            enforce_protocol(protocol)(target)  # type: ignore[arg-type]
            from typing import cast

            return cast(F, target)

        # Otherwise assume a callable executor.
        if protocol is not IExecutor:
            raise TypeError(
                "validated_protocol decorator can only be used with 'executor' "
                "alias when applied to functions."
            )
        _validate_executor_callable(target)
        return target

    return decorator


__all__ = [
    "validated_protocol",
]
