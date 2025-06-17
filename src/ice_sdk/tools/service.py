from __future__ import annotations

"""Simple registry & utility service for working with :pyclass:`~ice_sdk.tools.base.BaseTool` instances.

The implementation purposefully remains *minimal*.  The public surface exposed
by :class:`ToolService` is only what is currently needed by the rest of the
code-base (namely, instantiation, registering tools and a handful of helper
methods).  More sophisticated lifecycle management can be added later without
breaking the stable API.
"""

from typing import Any, Dict, Iterable, Type  # noqa: E402

from .base import BaseTool  # noqa: E402

__all__ = ["ToolService"]


class ToolService:  # noqa: D101 – simple façade
    _registry: Dict[str, Type[BaseTool]]

    def __init__(self, auto_register_builtins: bool = True) -> None:
        """Create a new *ToolService* instance.

        Args:
            auto_register_builtins: If *True* (default) the constructor will
                automatically register all built-in tools shipped with
                *ice_sdk* so they are readily available.
        """

        self._registry = {}
        if auto_register_builtins:
            self._register_default_tools()

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def register(self, tool_cls: Type[BaseTool]) -> None:
        """Register a new *tool class* so it can be instantiated by name."""
        if not issubclass(tool_cls, BaseTool):
            raise TypeError("tool_cls must inherit from BaseTool")
        if not getattr(tool_cls, "name", None):
            raise ValueError("Tool classes must define a unique `name` attribute")
        self._registry[tool_cls.name] = tool_cls

    def get(self, name: str, **init_kwargs: Any) -> BaseTool:
        """Instantiate and return the tool identified by *name*."""
        try:
            tool_cls = self._registry[name]
        except KeyError as exc:  # pragma: no cover – defensive branch
            raise KeyError(f"Tool '{name}' is not registered") from exc
        return tool_cls(**init_kwargs)  # type: ignore[call-arg]

    def available_tools(self) -> Iterable[str]:  # noqa: D401
        """Return an *iterator* over the names of registered tools."""
        return self._registry.keys()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _register_default_tools(self) -> None:
        """Register built-in tools shipped with *ice_sdk*."""
        # Import *inside* the method to avoid potential circular imports if
        # user code also imports from `ice_sdk` at module top-level.
        from .hosted import ComputerTool, FileSearchTool, WebSearchTool  # noqa: WPS433
        from .builtins import SleepTool, HttpRequestTool, SumTool  # noqa: WPS433

        for tool_cls in (
            WebSearchTool,
            FileSearchTool,
            ComputerTool,
            SleepTool,
            HttpRequestTool,
            SumTool,
        ):
            try:
                self.register(tool_cls)
            except Exception:  # noqa: BLE001 – best-effort registration
                # If a single tool fails to register (e.g. due to missing deps)
                # we ignore it so *ToolService* still provides the others.
                continue 