"""Tool execution service for the orchestrator runtime."""

import asyncio
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
        
        # Handle both sync and async execution
        if asyncio.iscoroutinefunction(execute_fn):
            result = await execute_fn(**inputs)
        else:
            # Run sync function in thread pool
            result = await asyncio.to_thread(execute_fn, **inputs)
        
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
        tool_class = registry._registry.get(NodeType.TOOL, {}).get(tool_name)  # type: ignore[attr-defined]
        if tool_class:
            try:
                return tool_class()  # type: ignore[no-any-return]
            except Exception:
                pass
        
        return None
    
    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all available tools with their metadata.
        
        Returns:
            Dictionary of tool names to metadata
        """
        tools = {}
        
        # Get all registered tools from unified registry
        tool_registry = registry._registry.get(NodeType.TOOL, {})  # type: ignore[attr-defined]
        
        for tool_name, tool_class in tool_registry.items():
            try:
                # Get tool metadata
                tools[tool_name] = {
                    "name": tool_name,
                    "description": tool_class.__doc__ or "No description",
                    "category": getattr(tool_class, "category", "general"),
                }
            except Exception:
                # Skip tools that can't be introspected
                pass
        
        return tools 