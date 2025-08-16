"""Tool execution service for the orchestrator runtime."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from ice_core.metrics import EXEC_COMPLETED, EXEC_STARTED
from ice_core.models import NodeType
from ice_core.protocols.node import INode
from ice_core.unified_registry import registry


class ToolExecutionService:
    """Handles tool execution within the orchestrator runtime."""

    async def execute_tool(
        self, tool_name: str, inputs: Dict[str, Any], context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute a tool by name with given inputs.

        Args:
            tool_name: Name of the tool to execute
            inputs: Input parameters for the tool
            context: Optional execution context

        Returns:
            Tool execution results

        Raises:
            ValueError: If tool not found
            Exception: If tool execution fails
        """
        # Get tool instance from registry
        tool_instance = self._get_tool_instance(tool_name)

        if tool_instance is None:
            from ice_core.exceptions import ToolFactoryResolutionError

            raise ToolFactoryResolutionError(tool_name, "not found in registry")

        # Execute the tool (inject execution context when supported)
        execute_fn = getattr(tool_instance, "execute", None)
        if execute_fn is None:
            from ice_core.exceptions import ToolFactoryResolutionError

            raise ToolFactoryResolutionError(tool_name, "missing execute() method")

        EXEC_STARTED.inc()
        # Handle both sync and async execution
        # Try to pass context/memory via conventional kw if accepted
        try:
            from inspect import signature

            sig = signature(execute_fn)
            if "context" in sig.parameters and context is not None:
                inputs = {**inputs, "context": context}
            if (
                "memory" in sig.parameters
                and context is not None
                and isinstance(context, dict)
            ):
                mem = context.get("memory")
                if mem is not None:
                    inputs = {**inputs, "memory": mem}
        except Exception:
            pass

        if asyncio.iscoroutinefunction(execute_fn):
            result = await execute_fn(**inputs)
        else:
            # Run sync function in thread pool
            result = await asyncio.to_thread(execute_fn, **inputs)

        EXEC_COMPLETED.inc()
        if result is None:
            result = {}
        if not isinstance(result, dict):
            try:
                result = dict(result)  # type: ignore[arg-type]
            except Exception:
                result = {"result": result}
        # Ensure str keys
        coerced: Dict[str, Any] = {str(k): v for k, v in result.items()}
        return coerced

    def _get_tool_instance(self, tool_name: str) -> Optional[INode]:
        """Get tool instance from unified registry.

        Tries, in order:
        1) Public factory API (register_tool_factory → get_tool_instance)
        2) Pre-instantiated instances map
        3) Class registry with direct instantiation
        """
        # 1) Preferred: public factory resolution
        try:
            from ice_core.unified_registry import get_tool_instance as _get_via_factory

            return _get_via_factory(tool_name)  # type: ignore[return-value]
        except Exception:
            pass

        # 2) Legacy: pre-instantiated instance lookup
        tool_instance = registry._instances.get(NodeType.TOOL, {}).get(tool_name)  # type: ignore[no-any-return]
        if tool_instance:
            return tool_instance

        # 3) Legacy: class registry
        tool_class = registry._nodes.get(NodeType.TOOL, {}).get(tool_name)  # type: ignore[attr-defined]
        if tool_class:
            try:
                return tool_class()  # type: ignore[no-any-return]
            except Exception:
                return None

        # No API fallback. Registry is the sole source of truth in-process.
        return None

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all available tools with their metadata.

        Returns:
            dict[str, dict[str, Any]]: Mapping of tool names to metadata dictionaries.
        """
        tools: Dict[str, Dict[str, Any]] = {}

        # Get all registered tools from unified registry
        # Collect both pre-instantiated and class-only tools
        tool_registry: Dict[str, Any] = {}
        # Instances already registered
        tool_registry.update(registry._instances.get(NodeType.TOOL, {}))  # type: ignore[attr-defined]
        # Classes that are registered but not yet instantiated
        tool_registry.update(registry._nodes.get(NodeType.TOOL, {}))  # type: ignore[attr-defined]

        for tool_name, tool_class in tool_registry.items():
            try:
                # Build tool metadata
                tools[tool_name] = {
                    "name": tool_name,
                    "description": tool_class.__doc__ or "No description",
                    "category": getattr(tool_class, "category", "general"),
                }
            except Exception:  # pragma: no cover – defensive
                # Skip tools that can't be introspected for whatever reason
                continue

        return tools

    # ------------------------------------------------------------------
    # Convenience helpers ----------------------------------------------
    # ------------------------------------------------------------------
    def available_tools(self) -> list[str]:  # noqa: D401 – simple name list helper
        """Return a list of all available tool names.

        This is a lightweight helper primarily for HTTP discovery endpoints that
        only need the names rather than full metadata.

        Returns:
            list[str]: All registered tool names.
        """
        return list(self.list_tools().keys())
