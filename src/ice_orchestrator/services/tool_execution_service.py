"""Tool execution service for the orchestrator runtime."""

from __future__ import annotations

import asyncio

from ice_core.metrics import EXEC_STARTED, EXEC_COMPLETED
from typing import Any, Dict, Optional

from ice_core.models import NodeType
from ice_core.protocols.node import INode
from ice_core.unified_registry import registry


class ToolExecutionService:
    """Handles tool execution within the orchestrator runtime."""
    
    async def execute_tool(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        context: Optional[Any] = None
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
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        
        # Execute the tool
        execute_fn = getattr(tool_instance, "execute", None)
        if execute_fn is None:
            raise ValueError(f"Tool '{tool_name}' has no execute method")
        
        EXEC_STARTED.inc()
        # Handle both sync and async execution
        if asyncio.iscoroutinefunction(execute_fn):
            result = await execute_fn(**inputs)
        else:
            # Run sync function in thread pool
            result = await asyncio.to_thread(execute_fn, **inputs)
        
        EXEC_COMPLETED.inc()
        return result  # type: ignore[no-any-return]
    
    def _get_tool_instance(self, tool_name: str) -> Optional[INode]:
        """Get tool instance from unified registry.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool instance or None if not found
        """
        # Try to get from unified registry
        tool_instance = registry._instances.get(NodeType.TOOL, {}).get(tool_name)  # type: ignore[no-any-return]
        
        if tool_instance:
            return tool_instance
        
        # Try to get class and instantiate
        tool_class = registry._nodes.get(NodeType.TOOL, {}).get(tool_name)  # type: ignore[attr-defined]
        if tool_class:
            try:
                return tool_class()  # type: ignore[no-any-return]
            except Exception:
                pass
        
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