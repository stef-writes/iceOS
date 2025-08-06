"""Namespace package for built-in iceOS toolkits.

Importing this sub-package **recursively imports** every module it contains so
that their registration side-effects run at start-up (exactly the same pattern
used in ``ice_tools.__init__``).  Putting the logic here makes sure tools that
live two levels deep, like ``ice_tools.toolkits.ecommerce.pricing_strategy``,
get imported even if the caller only does ``import ice_tools``.
"""
from __future__ import annotations

from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType
from typing import List, Sequence

_loaded: List[ModuleType] = []


def _recursive_import(package_name: str, pkg_path: Sequence[str]) -> None:
    for mod in iter_modules(pkg_path):
        full_name = f"{package_name}.{mod.name}"
        if mod.ispkg:
            sub_pkg = import_module(full_name)
            _recursive_import(full_name, sub_pkg.__path__)  # type: ignore[arg-type]
        else:
            _loaded.append(import_module(full_name))


# Kick-off deep import so every toolkit registers its tools right away
_recursive_import(__name__, __path__)  # type: ignore[arg-type]

__all__: list[str] = [m.__name__.split(".")[-1] for m in _loaded]
