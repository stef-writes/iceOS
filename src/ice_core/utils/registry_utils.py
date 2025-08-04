"""Registry validation utilities for tools and agents.

This module provides validation helpers to ensure all registered components
meet system requirements before they can be used in workflows.
"""
from __future__ import annotations

import inspect
from typing import Type, Union

from ice_core.base_node import BaseNode
from ice_core.base_tool import ToolBase
from ice_core.models.node_models import BaseNodeConfig

__all__ = ["RegistryError", "validate_registry_entry", "generate_default_metrics"]


class RegistryError(ValueError):
    """Base class for registry validation errors."""
    
    def __init__(self, message: str, component: Type[object]):
        super().__init__(f"{message} [Component: {component.__name__}]")
        self.component = component


def validate_registry_entry(entry: Type[Union[ToolBase, BaseNode]]) -> None:
    """Validate a registry entry meets all system requirements.
    
    Args:
        entry: Tool/Agent class being registered
        
    Raises:
        RegistryError: For any validation failure
    """
    # For tools, check they have proper execute method
    if hasattr(entry, 'execute'):
        if not inspect.iscoroutinefunction(entry.execute):
            raise RegistryError(".execute() must be async method", entry)
    
    # Validate async validation method only if present
    from ice_core.base_tool import ToolBase
    if hasattr(entry, 'validate') and issubclass(entry, BaseNode) and not issubclass(entry, ToolBase):
        if not inspect.iscoroutinefunction(getattr(entry, 'validate')):
            raise RegistryError(".validate() must be async method", entry)
    
    # Check for presence of metrics schema (optional for tools)
    if issubclass(entry, BaseNode) and not hasattr(entry, 'metrics_schema'):
        raise RegistryError("Missing metrics_schema class attribute", entry)


def generate_default_metrics(cls: Type[BaseNode]) -> dict:
    """Generate default metrics schema for agents missing one."""
    return {
        "type": "object",
        "properties": {
            "execution_time": {"type": "number"},
            "success": {"type": "boolean"},
            "error_count": {"type": "integer", "default": 0},
        },
        "required": ["execution_time", "success"],
    }