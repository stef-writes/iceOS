"""Auto-import generated tools and agents so registry factories register on import.

This makes `import ice_tools.generated` sufficient to register all contents.
"""

from __future__ import annotations

import importlib
import pkgutil

for _m in pkgutil.iter_modules(__path__):  # type: ignore[name-defined]
    importlib.import_module(f"{__name__}.{_m.name}")
