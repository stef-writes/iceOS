"""iceOS SDK."""

from .agents import AgentConfig, AgentNode, ModelSettings  # noqa: F401
from .base_node import BaseNode  # noqa: F401
from .context import GraphContextManager  # noqa: F401
from .models.config import LLMConfig, MessageTemplate  # noqa: F401
from .models.node_models import (  # noqa: F401
    NodeConfig,
    NodeExecutionResult,
    NodeMetadata,
)
from .tools.base import BaseTool, ToolContext, ToolError, function_tool  # noqa: F401
from .tools.hosted import ComputerTool, FileSearchTool, WebSearchTool  # noqa: F401
from .tools.service import ToolService  # noqa: F401

# NOTE: Lazy import of IceCopilot to avoid circular dependencies with ice_orchestrator.

__all__ = [
    # Core abstractions
    "BaseNode",
    "BaseTool",
    "ToolService",
    # Data models
    "NodeConfig",
    "NodeExecutionResult",
    "NodeMetadata",
    "LLMConfig",
    "MessageTemplate",
    # Context
    "GraphContextManager",
]

# Provide lazy attribute for IceCopilot ------------------------------------------------


def __getattr__(name: str):  # noqa: D401 – module hook
    if name == "IceCopilot":
        from importlib import import_module

        copilot_mod = import_module("ice_sdk.copilot")
        return getattr(copilot_mod, "IceCopilot")
    raise AttributeError(name)
