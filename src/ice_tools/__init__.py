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

for module_info in iter_modules(__path__):  # type: ignore[name-defined]
    if module_info.ispkg:
        # Skip sub-packages for now – keep footprint small
        continue
    module_name = f"{__name__}.{module_info.name}"
    _loaded.append(import_module(module_name))

__all__ = [m.__name__.split('.')[-1] for m in _loaded]
