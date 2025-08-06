"""Common, dependency-free tools that ship with iceOS.

Import side-effects: importing this package registers all contained tools with
the global registry so unit tests and examples can rely on
``tool_name`` look-ups without worrying about manual imports.
"""
from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType
from typing import List, Sequence

_loaded: List[ModuleType] = []

def _recursive_import(pkg_name: str, pkg_path: Sequence[str]) -> None:
    for mod in iter_modules(pkg_path):
        full_name = f"{pkg_name}.{mod.name}"
        _loaded.append(import_module(full_name))

_recursive_import(__name__, __path__)  # type: ignore[arg-type]

__all__: list[str] = [m.__name__.split(".")[-1] for m in _loaded]
