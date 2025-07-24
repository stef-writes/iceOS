"""Tool service for executing skills by name.

This module provides the ToolService class that acts as a registry and executor
for skills. It maintains a registry of tool classes and can instantiate and
execute them on demand.
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel

class ToolRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """Request payload consumed by :pymeth:`ToolService.execute`."""

    tool_name: str
    inputs: Dict[str, Any]
    context: Dict[str, Any]

class ToolService:  # – thin orchestration facade
    """Unified adapter that runs *Tool* implementations by name.

    The service acts as a lightweight compatibility layer between the
    orchestrator (which issues :class:`ToolRequest`s) and concrete *Tool*
    classes registered at runtime.  It purposefully remains **stateless** –
    each call to :pymeth:`execute` instantiates a new *Tool* object.
    """

    def __init__(self) -> None:
        # Eager-import built-in tool packages so their *register()* calls run
        # before we snapshot the global registry.  This prevents the
        # orchestrator from seeing an empty tool list when the API starts.

        import importlib

        for _pkg in (
            "ice_sdk.tools.system",
            "ice_sdk.tools.web",
            "ice_sdk.tools.db",
        ):
            try:  # best-effort
                importlib.import_module(_pkg)
            except ModuleNotFoundError:
                continue

        from importlib.metadata import entry_points, PackageNotFoundError  # lazily import
        from ice_sdk.unified_registry import registry
        from ice_core.models import NodeType

        # 1. Load any tools that were pre-registered via unified registry
        for key, tool_instance in registry._instances.items():
            if key.startswith(f"{NodeType.TOOL.value}:"):
                tool_name = key.split(":", 1)[1]
                self._registry.setdefault(tool_name, tool_instance.__class__)

        # 2. Discover additional tools via Python entry points ----------------
        try:
            eps = entry_points(group="ice_sdk.tools")  # type: ignore[arg-type]
            for ep in eps:
                try:
                    tool_cls = ep.load()
                    name = getattr(tool_cls, "name", ep.name)
                    self._registry.setdefault(name, tool_cls)
                except Exception:  # pragma: no cover – best-effort discovery
                    continue
        except PackageNotFoundError:  # pragma: no cover – no installed packages
            pass

        # 3. As final fallback, introspect built-in tool packages to harvest
        #    *ToolBase* subclasses when the on-import registration pattern
        #    failed (e.g. due to a single failing import wrapped in a broad
        #    try/except block).  This guarantees that development environments
        #    running from source still expose the full tool catalog without
        #    requiring a Poetry install step.

        from inspect import isclass
        from ice_sdk.tools.base import ToolBase

        import pkgutil

        def _harvest_from_module(module):
            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if not (isclass(obj) and issubclass(obj, ToolBase)):
                    continue

                # Pydantic models transform simple str attributes into
                # *FieldInfo* objects which raise ``AttributeError`` on
                # direct access.  Fallback to the raw ``__dict__`` and
                # model_fields for compatibility across versions.

                obj_name = None
                try:
                    obj_name = getattr(obj, "name")  # type: ignore[attr-defined]
                except AttributeError:
                    # Look into raw dict first ----------------------------------
                    obj_name = obj.__dict__.get("name")

                    # Then Pydantic v2 – default in model_fields if defined -----
                    if obj_name is None and hasattr(obj, "model_fields"):
                        _mf = obj.model_fields  # type: ignore[attr-defined]
                        if "name" in _mf:
                            obj_name = _mf["name"].default

                # End attribute resolution --------------------------------------

                if obj_name:
                    self._registry.setdefault(obj_name, obj)

        for _pkg in (
            "ice_sdk.tools.system",
            "ice_sdk.tools.web",
            "ice_sdk.tools.db",
        ):
            try:
                root_mod = importlib.import_module(_pkg)
            except ModuleNotFoundError:
                continue

            _harvest_from_module(root_mod)

            if hasattr(root_mod, "__path__"):
                for finder, name, ispkg in pkgutil.walk_packages(root_mod.__path__, prefix=f"{_pkg}."):
                    try:
                        sub_mod = importlib.import_module(name)
                        _harvest_from_module(sub_mod)
                    except Exception:
                        # Defensive – bad import in one tool shouldn't break entire registry
                        continue

    _registry: Dict[str, type] = {}

    # ------------------------------------------------------------------ API
    def register(self, tool_cls: type) -> None:  # – simple wrapper
        """Register *tool_cls* so it can be executed by name."""

        tool_name: str = getattr(tool_cls, "name", tool_cls.__name__)
        if tool_name in self._registry:
            # Duplicate registrations are ignored for idempotency – callers may
            # attempt to register the same class multiple times across tests.
            return
        self._registry[tool_name] = tool_cls

    def available_tools(self) -> list[str]:  # – enumeration helper
        """Return human-readable list of registered tool names (sorted)."""

        return sorted(self._registry.keys())

    # ------------------------------------------------------------------ metadata helpers
    # cards() method removed - capabilities system was over-engineered

    # ------------------------------------------------------------------ core
    async def execute(self, request: ToolRequest) -> Dict[str, Any]:
        """Instantiate the requested *Tool* and delegate execution.

        The method automatically detects whether :pymeth:`ToolBase.execute`
        is async or sync and routes accordingly so callers don't need to
        differentiate.
        """

        tool_cls = self._registry.get(request.tool_name)
        if tool_cls is None:
            # Attempt eager import of built-in system skills which auto-register
            try:
                import importlib

                importlib.import_module("ice_sdk.tools.system")
            except Exception:
                pass  # ignore failures – best effort

            tool_cls = self._registry.get(request.tool_name)

        if tool_cls is None:
            # Attempt fallback via unified registry --------------------
            try:
                from ice_sdk.unified_registry import registry  # local import
                from ice_core.models import NodeType

                key = f"{NodeType.TOOL.value}:{request.tool_name}"
                tool_instance_fallback = registry._instances.get(key)
                if tool_instance_fallback:
                    tool_cls = tool_instance_fallback.__class__
                    # Cache for future lookups
                    self._registry[request.tool_name] = tool_cls
                else:
                    raise ValueError(f"Tool '{request.tool_name}' not registered")
            except Exception as exc:  # pragma: no cover – final fallback
                raise ValueError(f"Tool '{request.tool_name}' not registered") from exc

        tool_instance = tool_cls()  # type: ignore[call-arg]

        exec_fn = getattr(tool_instance, "execute")
        if inspect.iscoroutinefunction(exec_fn):
            result = await exec_fn(request.inputs)  # type: ignore[arg-type]
        else:
            # Fallback – run sync implementation inside default executor to avoid
            # blocking the event loop.
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, exec_fn, request.inputs)

        # Maintain legacy wrapper structure expected by GraphContextManager
        return {"data": result}
