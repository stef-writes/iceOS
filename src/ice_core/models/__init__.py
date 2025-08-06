"""Domain models shared across layers.

These Pydantic models are generated from JSON Schema specs under the *schemas/*
folder or hand-written when appropriate.  They **must not** import from
higher-level packages such as *ice_orchestrator* or *ice_api*.
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
    # new execution-control node configs
    "SwarmNodeConfig",
    "HumanNodeConfig",
    "MonitorNodeConfig",
    "AgentSpec",
]

# Import protocols from ice_core.protocols
from ice_core.protocols import IEmbedder, IRegistry, ITool, IVectorIndex, IWorkflow

from ..protocols.node import INode

# AppConfig removed - runtime config doesn't belong in core layer
from .enums import ModelProvider, NodeType
from .llm import LLMConfig, MessageTemplate
from .node_metadata import NodeMetadata

# Node types removed - using definitions from node_models.py instead
from .node_models import (
    AgentNodeConfig,
    AgentSpec,
    BaseNodeConfig,
    ChainExecutionResult,
    ChainMetadata,
    ChainSpec,
    CodeNodeConfig,
    ConditionNodeConfig,
    ContextFormat,
    ContextRule,
    HumanNodeConfig,
    InputMapping,
    LLMOperatorConfig,
    LoopNodeConfig,
    MonitorNodeConfig,
    NodeConfig,
    NodeExecutionRecord,
    NodeExecutionResult,
    NodeIO,
    ParallelNodeConfig,
    RecursiveNodeConfig,
    RetryPolicy,
    SwarmNodeConfig,
    ToolConfig,
    ToolNodeConfig,
    UsageMetadata,
    WorkflowNodeConfig,
)

# Import base implementations
