"""Runtime plugin discovery helpers.

Contains **the only permitted** dynamic-import logic in the codebase.  All other
modules should import plugins explicitly or rely on dependency injection.
"""

from __future__ import annotations

import importlib.util as _importlib_util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import List, Type

from ice_sdk.skills import SkillBase

__all__: list[str] = ["discover_tools", "load_module_from_path"]


def load_module_from_path(path: Path) -> ModuleType:
    """Dynamically import Python module from *path* and return it.

    This function handles module name conflicts and ensures proper sys.path
    management for relative imports.
    """
    if not path.exists():
        raise FileNotFoundError(path)

    module_name = path.stem

    # When filename contains dots (e.g. hello_chain.chain.py) treat it as a
    # *single* module name by replacing dots with underscores so we avoid
    # ``my_chain.chain`` import errors.
    safe_module_name = module_name.replace(".", "_")

    # Drop previous import if exists --------------------------------------
    if safe_module_name in sys.modules:
        del sys.modules[safe_module_name]

    # Ensure the parent directory is on sys.path so relative imports work.
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))

    try:
        import importlib

        return importlib.import_module(safe_module_name)
    except ModuleNotFoundError:
        spec = _importlib_util.spec_from_file_location(safe_module_name, path)
        if spec and spec.loader:
            module = _importlib_util.module_from_spec(spec)
            sys.modules[safe_module_name] = module
            spec.loader.exec_module(module)  # type: ignore[arg-type]
            return module

        # If we reach here, loading failed
        raise


def _load_module_from_path(path: Path) -> ModuleType:
    """Dynamically import the Python file at *path* as a module.

    Legacy function for backward compatibility with existing tool discovery.
    """
    spec = _importlib_util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:  # pragma: no cover – safety net
        raise ImportError(f"Cannot import {path}")

    module = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


def discover_tools(root: Path | str) -> List[Type[SkillBase]]:  # noqa: D401
    """Return a list of *SkillBase* subclasses found under *root* directory."""
    root_path = Path(root)
    tool_classes: list[Type[SkillBase]] = []

    for path in root_path.rglob("*.tool.py"):
        try:
            mod = _load_module_from_path(path)
        except Exception:  # noqa: BLE001 – skip faulty modules
            continue

        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, SkillBase) and obj is not SkillBase:
                tool_classes.append(obj)

    return tool_classes
