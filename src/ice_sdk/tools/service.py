"""Simple registry & utility service for working with :pyclass:`~ice_sdk.tools.base.BaseTool` instances.

The implementation purposefully remains *minimal*.  The public surface exposed
by :class:`ToolService` is only what is currently needed by the rest of the
code-base (namely, instantiation, registering tools and a handful of helper
methods).  More sophisticated lifecycle management can be added later without
breaking the stable API.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, Type

from .base import BaseTool

if TYPE_CHECKING:  # pragma: no cover – for type checkers only
    from ice_sdk.capabilities.card import (  # noqa: WPS433 – optional import
        CapabilityCard,
    )

__all__ = ["ToolService"]


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

    def discover_and_register(self, directory: str | Path = ".", pattern: str = "*.tool.py") -> None:
        """Recursively import and register any *tool* modules found under *directory*.

        This implements the Day-3 "auto-registration of `*.tool.py` files" milestone.

        The function is *idempotent*: re-discovering the same directory twice
        will not raise – duplicate tool names are ignored with a warning.
        """

        import importlib
        import inspect
        import logging

        logger = logging.getLogger(__name__)

        base_path = Path(directory).resolve()

        import sys
        if str(base_path) not in sys.path:
            sys.path.insert(0, str(base_path))

        for py_file in base_path.rglob(pattern):
            # Compute importable module path (assuming it is on sys.path)
            try:
                rel_path = py_file.relative_to(base_path)
            except ValueError:
                rel_path = py_file.name  # type: ignore[assignment]

            module_name = Path(str(rel_path)).with_suffix("").as_posix().replace("/", ".")

            try:
                # Attempt normal import first --------------------------------
                try:
                    module = importlib.import_module(module_name)
                except ModuleNotFoundError:
                    # Fall back to loading directly from file path ----------
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(module_name.replace(".", "_"), py_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)  # type: ignore[reportGeneralTypeIssues]
                    else:
                        raise
            except Exception as exc:
                logger.warning("Could not import %s: %s", module_name, exc)
                continue

            # Inspect module attributes for *tool* subclasses -------------
            for obj in module.__dict__.values():
                if inspect.isclass(obj) and issubclass(obj, BaseTool):
                    tool_name = getattr(obj, "name", None)
                    try:
                        self.register(obj)
                        logger.info("Registered tool '%s' from %s", tool_name, module_name)
                    except ValueError:
                        # Duplicate registration – ignore silently so repeated scans are safe.
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
    # Internals
    # ------------------------------------------------------------------
    def _register_default_tools(self) -> None:
        """Register built-in tools shipped with *ice_sdk*."""
        # Import *inside* the method to avoid potential circular imports if
        # user code also imports from `ice_sdk` at module top-level.
        from .builtins import HttpRequestTool, SleepTool, SumTool  # noqa: WPS433
        from .hosted import ComputerTool, FileSearchTool, WebSearchTool  # noqa: WPS433

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