"""Decorators for the new node system."""
import functools
from typing import Any, Callable, Optional, Type, Dict

from ice_core.base_tool import ToolBase
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType


def tool(
    name: Optional[str] = None,
    auto_register: bool = True,
) -> Callable[[Type[ToolBase]], Type[ToolBase]]:
    """Simple decorator for tool classes with auto-registration.
    
    Args:
        name: Tool name for registry (defaults to class name in snake_case)
        auto_register: Automatically register in unified registry
        
    Example:
        @tool
        class CSVReaderTool(ToolBase):
            '''Reads and parses CSV files.'''
            
            async def _execute_impl(self, **kwargs):
                # ... implementation
    """
    def decorator(cls: Type[ToolBase]) -> Type[ToolBase]:
        # Validate it's a proper tool
        if not issubclass(cls, ToolBase):
            raise TypeError(f"{cls.__name__} must inherit from ToolBase")
            
        # Extract tool name - convert CamelCase to snake_case
        if name:
            tool_name = name
        else:
            # Convert "CSVReaderTool" -> "csv_reader" 
            class_name = cls.__name__.replace('Tool', '')
            tool_name = ''.join(['_' + c.lower() if c.isupper() and i > 0 else c.lower() 
                                for i, c in enumerate(class_name)]).lstrip('_')
        
        # Auto-register if requested
        if auto_register:
            # Create an instance for registration
            tool_instance = cls()
            registry.register_instance(NodeType.TOOL, tool_name, tool_instance)
            
        return cls
        
    return decorator 