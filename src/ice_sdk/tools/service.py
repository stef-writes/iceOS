"""Tool registry service for SDK - provides tool discovery only."""

from typing import Dict, List, Optional, Type
from ice_core.base_tool import ToolBase
from ice_core.unified_registry import registry
from ice_core.models import NodeType


class ToolService:
    """Tool registry service - provides discovery and registration only.
    
    This is a facade over the unified registry for tool management.
    Actual tool execution is handled by the orchestrator's ToolExecutionService.
    """
    
    def __init__(self) -> None:
        # Eagerly import built-in tool packages so their @tool decorators run
        import ice_sdk.tools.core
        import ice_sdk.tools.ai
        import ice_sdk.tools.system
        import ice_sdk.tools.web
        import ice_sdk.tools.db
        import ice_sdk.tools.marketplace
    
    def register_tool(self, name: str, tool_class: Type[ToolBase]) -> None:
        """Register a tool class in the unified registry.
        
        Args:
            name: Unique tool name
            tool_class: Tool class to register
        """
        registry.register_class(NodeType.TOOL, name, tool_class)
    
    def get_tool_class(self, name: str) -> Optional[Type[ToolBase]]:
        """Get a tool class by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool class or None if not found
        """
        tool_registry = registry._registry.get(NodeType.TOOL, {})
        return tool_registry.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names.
        
        Returns:
            List of tool names
        """
        tool_registry = registry._registry.get(NodeType.TOOL, {})
        return list(tool_registry.keys())
    
    def get_tool_metadata(self, name: str) -> Optional[Dict[str, any]]:
        """Get metadata for a tool.
        
        Args:
            name: Tool name
            
        Returns:
            Tool metadata or None if not found
        """
        tool_class = self.get_tool_class(name)
        if not tool_class:
            return None
        
        return {
            "name": name,
            "description": tool_class.__doc__ or "No description",
            "category": getattr(tool_class, "category", "general"),
        }
