"""Plugin discovery utilities relocated from *ice_sdk.plugin_discovery*.

Importing from ``ice_core.plugins.discovery`` is the new, canonical path.
During the transition we simply re-export the existing helpers so that any
remaining imports keep working until they are updated.
"""

from __future__ import annotations

from .discovery import discover_tools, load_module_from_path  # type: ignore

__all__: list[str] = [
    "discover_tools",
    "load_module_from_path",
]
