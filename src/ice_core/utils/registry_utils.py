"""Registry validation utilities for tools and agents.

This module provides validation helpers to ensure all registered components
meet system requirements before they can be used in workflows.
"""

from __future__ import annotations

import inspect
from typing import Any, Type, Union

from ice_core.base_node import BaseNode
from ice_core.base_tool import ToolBase

__all__ = ["RegistryError", "validate_registry_entry", "generate_default_metrics"]


from ice_core.exceptions import RegistryError  # Re-export canonical error


def validate_registry_entry(entry: Type[Union[ToolBase, BaseNode]]) -> None:
    """Validate a registry entry meets all system requirements.

    Args:
        entry: Tool/Agent class being registered

    Raises:
        RegistryError: For any validation failure
    """
    # For tools, check they have proper execute method
    if hasattr(entry, "execute"):
        if not inspect.iscoroutinefunction(entry.execute):
            raise RegistryError(f".execute() must be async method for {entry.__name__}")

    # Validate async validation method only if present
    from ice_core.base_tool import ToolBase

    if (
        hasattr(entry, "validate")
        and issubclass(entry, BaseNode)
        and not issubclass(entry, ToolBase)
    ):
        if not inspect.iscoroutinefunction(getattr(entry, "validate")):
            raise RegistryError(
                f".validate() must be async method for {entry.__name__}"
            )

    # Check for presence of metrics schema (optional for tools)
    if issubclass(entry, BaseNode) and not hasattr(entry, "metrics_schema"):
        raise RegistryError(
            f"Missing metrics_schema class attribute for {entry.__name__}"
        )


def generate_default_metrics(cls: Type[BaseNode]) -> dict[str, Any]:
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
