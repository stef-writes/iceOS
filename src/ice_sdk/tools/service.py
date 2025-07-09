"""Simple registry & utility service for working with :pyclass:`~ice_sdk.tools.base.BaseTool` instances.

The implementation purposefully remains *minimal*.  The public surface exposed
by :class:`ToolService` is only what is currently needed by the rest of the
code-base (namely, instantiation, registering tools and a handful of helper
methods).  More sophisticated lifecycle management can be added later without
breaking the stable API.
"""

from __future__ import annotations

import inspect  # NEW
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, Type

from pydantic import BaseModel  # NEW IMPORT

from .base import BaseTool, ToolContext

if TYPE_CHECKING:  # pragma: no cover – for type checkers only
    from ice_sdk.capabilities.card import (  # noqa: WPS433 – optional import
        CapabilityCard,
    )

__all__ = ["ToolService"]


class ToolRequest(BaseModel):
    """Payload model for executing a tool via the public API."""

    tool_name: str
    inputs: dict[str, Any] = {}
    context: dict[str, Any] | None = None


class ToolService:  # noqa: D101 – simple façade
    _registry: Dict[str, Type[BaseTool]]

    # ------------------------------------------------------------------
    # Construction & discovery -----------------------------------------
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # New feature: file-system discovery of ``*.tool.py`` ----------------
    # ------------------------------------------------------------------

    def discover_and_register(
        self, directory: str | Path = ".", pattern: str = "*.tool.py"
    ) -> None:
        """Recursively import and register any *tool* modules found under *directory*.

        This implements the Day-3 "auto-registration of `*.tool.py` files" milestone.

        The function is *idempotent*: re-discovering the same directory twice
        will not raise – duplicate tool names are ignored with a warning.
        """

        import logging

        logger = logging.getLogger(__name__)

        from ice_sdk.plugin_discovery import discover_tools

        base_path = Path(directory).resolve()

        for tool_cls in discover_tools(base_path):
            try:
                self.register(tool_cls)
                logger.info("Registered tool '%s'", tool_cls.name)
            except ValueError:
                continue

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
    # Capability cards --------------------------------------------------
    # ------------------------------------------------------------------

    def cards(self) -> Iterable["CapabilityCard"]:  # noqa: D401
        """Yield :class:`~ice_sdk.capabilities.card.CapabilityCard` for every registered tool.

        The method is intentionally *lazy* (uses a generator) so callers can
        iterate without materialising the full list.
        """

        # Local import to avoid an *optional* dependency when callers never
        # request capability cards.
        from ice_sdk.capabilities.card import CapabilityCard

        for tool_cls in self._registry.values():
            yield CapabilityCard.from_tool_cls(tool_cls)

    # ------------------------------------------------------------------
    # Direct execution API ---------------------------------------------
    # ------------------------------------------------------------------
    async def execute(self, request: "ToolRequest") -> dict[str, Any]:
        """Execute the *tool* described by *request* and return its result.

        This replaces the now-deprecated MCP indirection layer with a direct
        registry lookup followed by an asynchronous ``run`` call on the tool
        instance. Schema validation (if any) should be enforced by individual
        tool implementations.
        """

        # Instantiate the requested tool (raises *KeyError* if unknown)
        tool = self.get(request.tool_name)

        # Merge context into kwargs if the tool accepts a ``ctx`` parameter
        run_sig = inspect.signature(tool.run)  # type: ignore[attr-defined]
        kwargs = dict(request.inputs)
        if "ctx" in run_sig.parameters and request.context is not None:
            kwargs["ctx"] = ToolContext(**request.context)  # type: ignore[call-arg]

        # Execute – handle sync & async implementations transparently
        if inspect.iscoroutinefunction(tool.run):  # type: ignore
            result = await tool.run(**kwargs)  # type: ignore[arg-type]
        else:  # pragma: no cover – most tools are async but guard anyway
            result = tool.run(**kwargs)  # type: ignore[arg-type]

        return {"data": result, "tool": tool.name}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _register_default_tools(self) -> None:
        """Register built-in tools shipped with *ice_sdk*."""
        # Local imports kept inside the method to prevent circular deps -----------
        from .builtins import (  # noqa: WPS433; noqa: WPS433 – newly added deterministic tools
            CsvLoaderTool,
            HttpRequestTool,
            JsonQueryTool,
            PdfExtractTool,
            SleepTool,
            SumTool,
        )
        from .hosted import ComputerTool, FileSearchTool, WebSearchTool  # noqa: WPS433
        from .mcp_tool import MCPTool  # noqa: WPS433 – new generic MCP integration tool
        from .webhook import WebhookEmitterTool  # noqa: WPS433 – new tool

        for tool_cls in (
            # Data handling ---------------------------------------------------
            CsvLoaderTool,
            JsonQueryTool,
            PdfExtractTool,
            WebSearchTool,
            FileSearchTool,
            ComputerTool,
            SleepTool,
            HttpRequestTool,
            SumTool,
            WebhookEmitterTool,
            MCPTool,
        ):
            try:
                self.register(tool_cls)
            except Exception:  # noqa: BLE001 – best-effort registration
                # If a single tool fails to register (e.g. due to missing deps)
                # we ignore it so *ToolService* still provides the others.
                continue
