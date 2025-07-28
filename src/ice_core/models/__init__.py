"""Domain models shared across layers.

These Pydantic models are generated from JSON Schema specs under the *schemas/*
folder or hand-written when appropriate.  They **must not** import from
higher-level packages such as *ice_sdk* or *ice_orchestrator*.
"""

from __future__ import annotations

__all__: list[str] = [
    # Protocol
    "INode",
    "NodeExecutionResult",
    # Types
    "NodeType", 
    "BaseNodeConfig",
    "RetryPolicy",
    # Existing exports
    "NodeMetadata",
    "ModelProvider",
    "LLMConfig",
    "MessageTemplate",
    # AppConfig removed - runtime config doesn't belong in core layer
    "NodeConfig",
    "ToolNodeConfig",
    "LLMOperatorConfig",
    "AgentNodeConfig",
    "ConditionNodeConfig",
    "WorkflowNodeConfig",
    "LoopNodeConfig",
    "ParallelNodeConfig",
    "RecursiveNodeConfig",
    "CodeNodeConfig",
    "ChainExecutionResult",
    "ChainMetadata",
    "ContextFormat",
    "ContextRule",
    "InputMapping",
    "ToolConfig",
    "NodeExecutionRecord",
    "NodeIO",
    "UsageMetadata",
    "ChainSpec",
    # Node configs that don't exist yet are removed
    # Protocols
    "ITool",
    "IRegistry",
    "IVectorIndex",
    "IEmbedder",
    "IWorkflow",
    # Base implementations removed - they're in ice_core.base
]

# AppConfig removed - runtime config doesn't belong in core layer
from .enums import ModelProvider, NodeType
from .llm import LLMConfig, MessageTemplate
from .node_metadata import NodeMetadata
from ..protocols.node import INode
# Node types removed - using definitions from node_models.py instead
from .node_models import (
    BaseNodeConfig,
    RetryPolicy,
    ChainExecutionResult,
    ChainMetadata,
    ChainSpec,
    ToolNodeConfig,
    LLMOperatorConfig,
    AgentNodeConfig,
    ConditionNodeConfig,
    WorkflowNodeConfig,
    LoopNodeConfig,
    ParallelNodeConfig,
    RecursiveNodeConfig,
    CodeNodeConfig,
    ContextFormat,
    ContextRule,
    InputMapping,
    NodeConfig,
    NodeExecutionRecord,
    NodeExecutionResult,
    NodeIO,
    ToolConfig,
    UsageMetadata,
)

# Import protocols from ice_core.protocols
from ice_core.protocols import (
    ITool,
    IRegistry,
    IVectorIndex,
    IEmbedder,
    IWorkflow,
)

# Import base implementations
from ..base_node import BaseNode
from ..base_tool import ToolBase
