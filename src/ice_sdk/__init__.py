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

# from .models.network import NetworkSpec  # noqa: F401
from .services import ServiceLocator  # noqa: F401
from .tools.base import SkillBase, ToolContext, SkillExecutionError, function_tool  # noqa: F401
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
    # "NetworkSpec",  # not yet stable
    "LLMConfig",
    "MessageTemplate",
    # Context
    "GraphContextManager",
    # (RuntimeConfig & BudgetEnforcer intentionally NOT part of stable API)
]

# Removed IceCopilot – Copilot package deprecated

# NOTE: The previous dynamic __getattr__ hook was removed to make dependencies
# explicit and avoid hidden import side-effects. Downstream code must now import
# `IceCopilot` explicitly or receive it via dependency injection.

__all__.extend(["ServiceLocator"])

# Nested chain features intentionally not part of stable public surface yet
