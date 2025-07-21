"""Tool service for executing skills by name.

This module provides the ToolService class that acts as a registry and executor
for skills. It maintains a registry of skill classes and can instantiate and
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
    """Unified adapter that runs *Skill* implementations by name.

    The service acts as a lightweight compatibility layer between the
    orchestrator (which issues :class:`ToolRequest`s) and concrete *Skill*
    classes registered at runtime.  It purposefully remains **stateless** –
    each call to :pymeth:`execute` instantiates a new *Skill* object.
    """

    _registry: Dict[str, type] = {}

    # ------------------------------------------------------------------ legacy discovery
    def discover_and_register(self, path: "Path") -> None:  # noqa: D401
        """Legacy no-op stub.

        Older GraphContextManager versions called this method to auto-register
        skills discovered in the workspace.  The actual discovery logic was
        removed during the v0.10 refactor.  We keep a harmless placeholder so
        that dependent code can still run without attribute errors while the
        new plugin system matures.
        """

        # TODO: Re-implement proper plugin discovery in a dedicated registry.
        _ = path  # Quell unused variable warning

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
    def cards(self) -> List[Any]:
        """Return :class:`CapabilityCard` instances for each registered tool."""

        try:
            from ice_sdk.capabilities.card import (
                CapabilityCard,  # local import to avoid cycles
            )

            return [CapabilityCard.from_tool_cls(cls) for cls in self._registry.values()]  # type: ignore[arg-type]
        except Exception:  # pragma: no cover – soft dependency
            # Fallback when *capabilities* package is unavailable in minimal builds
            return []

    # ------------------------------------------------------------------ core
    async def execute(self, request: ToolRequest) -> Dict[str, Any]:
        """Instantiate the requested *Skill* and delegate execution.

        The method automatically detects whether :pymeth:`SkillBase.execute`
        is async or sync and routes accordingly so callers don't need to
        differentiate.
        """

        tool_cls = self._registry.get(request.tool_name)
        if tool_cls is None:
            # Attempt eager import of built-in system skills which auto-register
            try:
                import importlib

                importlib.import_module("ice_sdk.skills.system")
            except Exception:
                pass  # ignore failures – best effort

            tool_cls = self._registry.get(request.tool_name)

        if tool_cls is None:
            # Attempt fallback via global_skill_registry --------------------
            try:
                from ice_sdk.registry.skill import global_skill_registry  # local import

                tool_instance_fallback = global_skill_registry.get(request.tool_name)
                tool_cls = tool_instance_fallback.__class__
                # Cache for future lookups
                self._registry[request.tool_name] = tool_cls
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
