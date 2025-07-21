"""iceOS SDK."""

# ---------------------------------------------------------------------------
# Public agent-facing exports (moved from deprecated ``ice_sdk.agents`` package)
# ---------------------------------------------------------------------------


# Keep AgentConfig & ModelSettings re-export unchanged (order after AgentNode)

# Re-export AgentNode for orchestrator compatibility
from .agents.agent_node import AgentNode
from .base_node import BaseNode
from .context import GraphContextManager
from .models.config import LLMConfig, MessageTemplate
from .models.node_models import NodeConfig, NodeExecutionResult, NodeMetadata

# from .models.network import NetworkSpec
from .skills import SkillBase
from .skills.service import ToolService

# NOTE: Lazy import of IceCopilot to avoid circular dependencies with ice_orchestrator.

__all__ = [
    # Core abstractions
    "BaseNode",
    "SkillBase",  # supplant BaseTool alias
    "ToolService",
    "AgentNode",
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
