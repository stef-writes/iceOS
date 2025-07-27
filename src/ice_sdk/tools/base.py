"""Tool base class and utilities for iceOS SDK."""

from typing import Any, Callable, Dict, Type
from functools import wraps

from ice_core.base_tool import ToolBase as CoreToolBase
from ice_core.base_node import BaseNode

# Re-export ToolBase from core
ToolBase = CoreToolBase

# Export commonly used symbols
__all__ = [
    "ToolBase",
]
