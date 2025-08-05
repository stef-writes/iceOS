"""Decorator utilities to mark public API symbols.

Renamed from *public.py* during v0.9 refactor; kept API intact.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any, Callable, TypeVar, overload

__all__: list[str] = ["public"]

_T = TypeVar("_T", bound=Any)

def _get_module(obj: _T) -> ModuleType:  # pragma: no cover – trivial helper
    return sys.modules[obj.__module__]

from typing import Union, Callable

def public(obj: _T | None = None, *, name: str | None = None) -> Union[_T, Callable[[_T], _T]]:
    """Mark *obj* as part of the public API of its defining module."""

    def _decorator(target: _T) -> _T:
        module = _get_module(target)
        export_name = name or target.__name__
        symbols: list[str] = getattr(module, "__all__", [])
        if export_name not in symbols:
            symbols.append(export_name)
            setattr(module, "__all__", symbols)
        return target

    if obj is not None:
        return _decorator(obj)

    return _decorator
