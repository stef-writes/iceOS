"""Decorators for the new node system."""
from typing import Type, Any, Optional
from functools import wraps
from ice_core.models import NodeType
from ice_sdk.unified_registry import registry

def tool(name: Optional[str] = None):
    """Decorator to register a tool with the unified registry.
    
    Usage:
        @tool("my_tool")
        class MyTool(ToolBase):
            ...
            
        @tool  # Uses class name
        class MyTool(ToolBase):
            ...
    """
    def decorator(cls: Type[Any]) -> Type[Any]:
        tool_name = name or getattr(cls, 'name', None) or cls.__name__.lower()
        
        # Register as a class so it can be instantiated on demand
        registry.register_class(NodeType.TOOL, tool_name, cls)
        
        return cls
    
    # Handle both @tool and @tool("name") syntax
    if name and callable(name):
        # Called as @tool without parentheses
        cls = name
        name = None
        return decorator(cls)
    
    return decorator

# Removed skill alias - use @tool directly 