"""Plugin discovery utilities.

Importing from ``ice_core.plugins.discovery`` is the canonical path.
This module provides utilities for discovering and loading plugins.
"""

from __future__ import annotations

from .discovery import discover_tools, load_module_from_path  # type: ignore

__all__: list[str] = [
    "discover_tools",
    "load_module_from_path",
]
