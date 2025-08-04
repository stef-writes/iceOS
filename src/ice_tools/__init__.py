"""Built-in sample tools shipped with iceOS.

Importing this package registers all included tool classes via the
`@tool` decorator, so they become discoverable through the unified
registry and API discovery endpoints.

Runtime side-effects are limited to registration – all heavy logic lives
in each tool's `_execute_impl` method in accordance with rule #2.
"""

from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType
from typing import List

# ---------------------------------------------------------------------------
# Auto-import all sub-modules so their `@tool` decorations run immediately
# ---------------------------------------------------------------------------

_loaded: List[ModuleType] = []

def _recursive_import(package_name: str, pkg_path):  # noqa: D401 – helper
    """Recursively import *all* modules under *package_name* so that tool
    registration side-effects run exactly once at startup."""
    for mod in iter_modules(pkg_path):
        full_name = f"{package_name}.{mod.name}"
        if mod.ispkg:
            sub_pkg = import_module(full_name)
            _recursive_import(full_name, sub_pkg.__path__)  # type: ignore[arg-type]
        else:
            _loaded.append(import_module(full_name))


_recursive_import(__name__, __path__)  # type: ignore[arg-type]

__all__ = [m.__name__.split('.')[-1] for m in _loaded]
