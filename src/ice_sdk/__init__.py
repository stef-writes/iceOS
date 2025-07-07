"""iceOS SDK."""

from . import extensions  # noqa: F401
from .agents import AgentConfig, AgentNode, ModelSettings  # noqa: F401
from .base_node import BaseNode  # noqa: F401
from .context import GraphContextManager  # noqa: F401
from .models.config import LLMConfig, MessageTemplate  # noqa: F401
from .models.node_models import (  # noqa: F401
    NodeConfig,
    NodeExecutionResult,
    NodeMetadata,
)
from .services import ServiceLocator  # noqa: F401
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
    # Extensions
    "extensions",
]

# Provide IceCopilot symbol directly (constructor injection elsewhere) -----------
try:
    from .copilot import IceCopilot  # noqa: F401 – optional high-level helper

    __all__.append("IceCopilot")
except Exception:  # pragma: no cover – optional dependency missing / circular issues
    # Do not fail import if Copilot has unmet deps; users can still use core SDK.
    pass

# NOTE: The previous dynamic __getattr__ hook was removed to make dependencies
# explicit and avoid hidden import side-effects. Downstream code must now import
# `IceCopilot` explicitly or receive it via dependency injection.

__all__.extend(["ServiceLocator"])
