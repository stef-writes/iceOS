"""Light-weight deprecation helpers.

Designed to be imported from any layer without dragging heavy deps.

Usage
-----
>>> from ice_core.utils.deprecation import deprecated
>>> @deprecated('0.9', replacement='ice_core.models.User')
... class OldUser: ...
"""

from __future__ import annotations

import os
import sys
import warnings
from functools import wraps
from typing import Any, Callable, TypeVar

from ice_core.exceptions import DeprecatedError

F = TypeVar("F", bound=Callable[..., Any])


DEFAULT_STACKLEVEL = 3  # Show the *caller* of the deprecated symbol


def _build_message(obj_name: str, version: str, replacement: str | None) -> str:
    msg = f"{obj_name} is deprecated and will be removed in a future release; introduced in {version}."
    if replacement:
        msg += f"  Use {replacement} instead."
    return msg


def _warn_or_error(message: str) -> None:  # noqa: D401 – imperative mood
    """Emit a :class:`DeprecationWarning` or raise :class:`DeprecatedError`.

    The behaviour is controlled by the env var ``ICE_STRICT_SHIMS``.  When set to
    ``1`` (opt-in), any access to deprecated symbol fails immediately in order
    to aid CI migration.
    """

    if os.getenv("ICE_STRICT_SHIMS") == "1":
        raise DeprecatedError(message)
    warnings.warn(message, DeprecationWarning, stacklevel=DEFAULT_STACKLEVEL)


def deprecated(version: str, replacement: str | None = None) -> Callable[[F], F]:
    """Decorator to mark callables/classes as deprecated.

    Parameters
    ----------
    version:
        Version in which the symbol became deprecated (informational).
    replacement:
        Dotted path to the preferred symbol, if any.
    """

    def decorator(obj: F) -> F:  # type: ignore[misc]
        message = _build_message(obj.__name__, version, replacement)

        @wraps(obj)  # type: ignore[arg-type]
        def wrapped(*args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
            _warn_or_error(message)
            return obj(*args, **kwargs)

        # Preserve metadata for introspection/testing
        wrapped.__deprecated__ = True  # type: ignore[attr-defined]
        wrapped.__deprecated_message__ = message  # type: ignore[attr-defined]
        return wrapped  # type: ignore[return-value]

    return decorator


def deprecate_module(version: str, replacement: str | None = None) -> None:
    """Mark the *calling* module as deprecated.

    Should be invoked at the *top* of a shim module::

        # my_shim.py
        from ice_core.utils.deprecation import deprecate_module
        deprecate_module("0.9", replacement="new.path")
    """

    caller_frame = sys._getframe(1)
    module_name: str | None = caller_frame.f_globals.get("__name__")  # type: ignore[assignment]
    if module_name is None:
        return  # pragma: no cover – cannot happen in normal Python runtime

    message = _build_message(module_name, version, replacement)
    _warn_or_error(message)

    # Expose metadata for tests
    mod_obj = sys.modules.get(module_name)
    if mod_obj is not None:  # pragma: no branch – defensive
        setattr(mod_obj, "__deprecated__", True)
        setattr(mod_obj, "__deprecated_message__", message)
