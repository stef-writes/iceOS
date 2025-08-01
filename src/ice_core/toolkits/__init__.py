"""Toolkit abstractions for grouping related iceOS tools.

A *toolkit* is **not** executable by itself.  It is a *factory* that validates
configuration, declares optional runtime dependencies and returns a collection
of fully-initialised :class:`ice_core.base_tool.ToolBase` instances.

The concept is inspired by LangChain's toolkits but implemented from scratch to
respect iceOS architectural rules (async I/O, Pydantic validation, strict type
hints, and clear layer boundaries).
"""

from __future__ import annotations

from .base import BaseToolkit  # noqa: F401

__all__: list[str] = [
    "BaseToolkit",
]
