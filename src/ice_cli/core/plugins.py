"""Plugin discovery utilities for the *ice* CLI.

This module centralises plugin loading so other components (e.g. tests or
embedded runtimes) can import :func:`discover_plugins` without depending on the
Typer root application.  The helper performs a best-effort import of every
module under the *ice_cli.plugins* package.  Each plugin is expected to expose
one or more Typer ``app`` objects at module level so that the main CLI can
mount them automatically.
"""

from __future__ import annotations

import pkgutil
from importlib import import_module as _import_module
from types import ModuleType
from typing import List

from rich import print as rprint  # type: ignore  # Third-party

__all__ = ["discover_plugins"]


def discover_plugins(
    package: str = "ice_cli.plugins",
) -> List[ModuleType]:  # noqa: D401
    """Import all modules within *package* so their Typer apps register.

    Parameters
    ----------
    package: str, optional
        Dotted path to the plugins namespace.  Defaults to ``"ice_cli.plugins"``.

    Returns
    -------
    List[ModuleType]
        Sequence of successfully imported plugin modules (order preserved).
    """

    try:
        pkg = _import_module(package)
    except ModuleNotFoundError:
        return []  # Graceful exit when no plugins package available

    modules: List[ModuleType] = []
    for mod_info in pkgutil.iter_modules(pkg.__path__, prefix=f"{package}."):
        try:
            modules.append(_import_module(mod_info.name))
        except Exception as exc:  # noqa: BLE001 – best-effort load
            # Fall back to *print* when Rich unavailable (unlikely inside CLI).
            try:
                rprint(f"[yellow]Failed to load plugin {mod_info.name}: {exc}")
            except Exception:  # pragma: no cover – minimal fallback
                print(f"Failed to load plugin {mod_info.name}: {exc}")

    return modules
