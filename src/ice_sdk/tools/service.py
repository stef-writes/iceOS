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
        
        # 🚀 NEW: Import built-in tools (they are optional and configurable)
        import ice_sdk.tools.builtin
    
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
        try:
            return registry.get_class(NodeType.TOOL, name)
        except Exception:
            return None
    
    def list_tools(self) -> List[str]:
        """List all registered tool names.
        
        Returns:
            List of tool names
        """
        tools = registry.list_nodes(NodeType.TOOL)
        return [name for node_type, name in tools]
    
    def available_tools(self) -> List[str]:
        """Get available tool names - alias for list_tools() for API compatibility."""
        return self.list_tools()
    
    def get_builtin_tools(self) -> List[str]:
        """Get list of built-in tools that are auto-registered.
        
        Returns:
            List of built-in tool names
        """
        builtin_tools = [
            "post_execution_mermaid",
            "workflow_analyzer", 
            "execution_summarizer",
            "performance_profiler"
        ]
        
        # Return only those that are actually registered
        return [tool for tool in builtin_tools if registry.has_tool(tool)]
    
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
