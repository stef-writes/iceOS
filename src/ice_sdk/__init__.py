"""ice_sdk – core abstraction layer.

This package exposes:

* **BaseNode** – async computation unit with typed inputs/outputs.
* **BaseTool** – gateway for side-effecting operations (DB, HTTP…).
* Runtime helper functions to discover/register *Tools* and *Nodes* via
  entry-points (see `iter_tool_classes()`, `iter_node_classes()`).

Nothing in `ice_sdk` should import from `app.*`; it stays framework-only so
external projects can depend on it without pulling the reference application.
"""

# ---------------------------------------------------------------------------
# Imports (must appear before other module-level code per PEP8 / Ruff E402)
# ---------------------------------------------------------------------------

import logging as _logging
import os as _os
from importlib import metadata as _metadata
from typing import Dict, Type

import structlog as _structlog

from ice_sdk.base_node import BaseNode
from ice_sdk.base_tool import BaseTool

# Public interfaces -------------------------------------------------------


__all__ = [
    "BaseNode",
    "BaseTool",
    "ToolService",
]

# The SDK also exposes registries for plugins (tools, nodes, etc.)

_TOOL_ENTRYPOINT_GROUP = "ice.tools"
_NODE_ENTRYPOINT_GROUP = "ice.nodes"

_tools_cache: Dict[str, Type[BaseTool]] | None = None
_nodes_cache: Dict[str, Type[BaseNode]] | None = None


def _load_entrypoints(group: str):
    """Helper to lazily load entry points from *group*."""
    try:
        eps = _metadata.entry_points()
    except Exception:  # pragma: no cover – importlib.metadata behaviour differs <3.10
        eps = {}
    return eps.select(group=group) if hasattr(eps, "select") else eps.get(group, [])


def iter_tool_classes():
    global _tools_cache
    if _tools_cache is None:
        _tools_cache = {}
        for ep in _load_entrypoints(_TOOL_ENTRYPOINT_GROUP):
            try:
                cls = ep.load()
                if hasattr(cls, "name"):
                    _tools_cache[cls.name] = cls
            except Exception:  # pylint: disable=broad-except
                # Ignore broken entrypoints but keep going
                continue

    # -----------------------------------------------------------------
    # Fallback: ensure built-in tools packaged in `ice_tools.builtins` are
    # available even when entry points are not configured (e.g., in a dev
    # checkout).  This keeps backward-compatibility while encouraging
    # external packages to rely on entry-points in production.
    # -----------------------------------------------------------------
    if not _tools_cache:
        try:
            import pkgutil
            from importlib import import_module

            builtins_pkg = import_module("ice_tools.builtins")
            for _, mod_name, _ in pkgutil.iter_modules(builtins_pkg.__path__):
                try:
                    mod = import_module(f"ice_tools.builtins.{mod_name}")
                    for attr in mod.__dict__.values():
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseTool)
                            and attr is not BaseTool
                        ):
                            _tools_cache[attr.name] = attr
                except Exception:
                    continue
        except ModuleNotFoundError:
            # builtins package missing – ignore
            pass

    return _tools_cache.values()


def get_tool_class(name: str) -> Type[BaseTool] | None:
    if _tools_cache is None:
        list(iter_tool_classes())  # populate cache
    return _tools_cache.get(name)


def iter_node_classes():
    global _nodes_cache
    if _nodes_cache is None:
        _nodes_cache = {}
        for ep in _load_entrypoints(_NODE_ENTRYPOINT_GROUP):
            try:
                cls = ep.load()
                # Use the declared discriminator (e.g., 'ai', 'tool') if
                # it exists, otherwise default to the lowercase class
                # name.  This aligns with `NodeConfig.type` semantics.
                discriminator = getattr(cls, "type", cls.__name__.lower())
                _nodes_cache[discriminator] = cls
            except Exception:
                continue
    return _nodes_cache.values()


def get_node_class(name: str):
    if _nodes_cache is None:
        list(iter_node_classes())
    return _nodes_cache.get(name)


# ---------------------------------------------------------------------------
# Default structlog configuration – JSON to stdout when not configured by
# the host application.  This keeps the change backwards-compatible and
# ensures we always have structured logs for cloud ingestion.
# ---------------------------------------------------------------------------

if not _structlog.is_configured():  # Avoid overriding app-specific config.
    # Resolve logging level string (e.g., "INFO", "DEBUG") to its numeric value.
    _level_name = _os.getenv("ICE_LOG_LEVEL", "INFO").upper()
    _level = getattr(_logging, _level_name, _logging.INFO)

    _structlog.configure(
        processors=[
            _structlog.processors.TimeStamper(fmt="iso"),
            _structlog.processors.add_log_level,
            _structlog.processors.StackInfoRenderer(),
            _structlog.processors.format_exc_info,
            _structlog.processors.JSONRenderer(),
        ],
        wrapper_class=_structlog.make_filtering_bound_logger(min_level=_level),
        cache_logger_on_first_use=True,
    )

# Deferred import to avoid circular dependency with tool_service accessing
# iter_tool_classes during its module import.
from ice_sdk.tool_service import (  # noqa: E402  (import placed late intentionally to avoid circular refs)
    ToolService,
)
