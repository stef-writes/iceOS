"""Utility decorator to mark symbols as part of a module's public API.

The :pyfunc:`@public` decorator appends the decorated object's *qualified name*
(`obj.__name__`) to the ``__all__`` list on the **defining** module.  This
ensures that the public contract is centralised and keeps individual modules
DRY and self-documenting.

Examples
--------
>>> from ice_sdk.utils.public import public
>>> @public  # doctest: +SKIP
... class Greeter:
...     def greet(self, name: str) -> str:
...         return f"Hello {name}!"

The class ``Greeter`` is now exported when a consumer executes
``from my_module import *`` and appears in static analyzers via the
``__all__`` contract.

Notes
-----
* The decorator is **idempotent** – applying it multiple times will not create
  duplicate entries in ``__all__``.
* If a module defines no ``__all__`` list yet, one is created lazily.

"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any, Callable, TypeVar, overload

__all__: list[str] = ["public"]

_T = TypeVar("_T", bound=Any)


def _get_module(obj: _T) -> ModuleType:  # pragma: no cover – trivial helper
    """Return the module in which *obj* is defined."""

    return sys.modules[obj.__module__]


@overload
def public(obj: _T) -> _T:  # noqa: D401 – simple decorator signature
    """Mark *obj* as part of the public API of its defining module."""


@overload
def public(*, name: str | None = None) -> Callable[[_T], _T]:
    """Decorate *obj* and optionally override its exported *name*.

    Parameters
    ----------
    name: str | None, optional
        Alternative symbol name to export instead of ``obj.__name__``. Useful
        when re-exporting under an alias.
    """


def public(obj: _T | None = None, *, name: str | None = None) -> _T | Callable[[_T], _T]:  # type: ignore[override]
    """Implementation of :pyfunc:`public` decorator (see overloads)."""

    def _decorator(target: _T) -> _T:
        module = _get_module(target)
        export_name = name or target.__name__

        # Lazily create __all__ if missing.  Use getattr to avoid AttributeError.
        symbols: list[str] = getattr(module, "__all__", [])
        if export_name not in symbols:
            symbols.append(export_name)
            setattr(module, "__all__", symbols)
        return target

    # Support usage with or without parentheses.
    if obj is not None:
        return _decorator(obj)

    return _decorator
