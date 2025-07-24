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
    "AppConfig",
    "NodeConfig",
    "LLMOperatorConfig",
    "ToolNodeConfig",
    "ConditionNodeConfig",
    "NestedChainConfig",
    "AgentNodeConfig",
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
    # New node configs
    "LLMNodeConfig",
    "UnitNodeConfig",
    "WorkflowNodeConfig",
    "LoopNodeConfig",
    "ParallelNodeConfig",
    "CodeNodeConfig",
    # Protocols
    "ITool",
    "IRegistry",
    "IVectorIndex",
    "IEmbedder",
    "IWorkflow",
    # Base implementations
    "BaseNode",
    "ToolBase",
]

from .app_config import AppConfig
from .enums import ModelProvider, NodeType
from .llm import LLMConfig, MessageTemplate
from .node_metadata import NodeMetadata
from ..protocols.node import INode
from .node_types import (
    BaseNodeConfig,
    RetryPolicy,
    LLMNodeConfig,
    UnitNodeConfig,
    WorkflowNodeConfig,
    LoopNodeConfig,
    ParallelNodeConfig,
    CodeNodeConfig,
)
from .node_models import (
    ChainExecutionResult,
    ChainMetadata,
    ChainSpec,
    ConditionNodeConfig,
    ContextFormat,
    ContextRule,
    InputMapping,
    LLMOperatorConfig,
    NestedChainConfig,
    NodeConfig,
    NodeExecutionRecord,
    NodeExecutionResult,
    NodeIO,
    AgentNodeConfig,
    ToolConfig,
    UsageMetadata,
    ToolNodeConfig,
)

# Import protocols from new location
from ..protocols import (
    INode as INodeProtocol,  # Alias to avoid conflict
    ITool,
    IRegistry,
    IVectorIndex,
    IEmbedder,
    IWorkflow,
)

# Import base implementations
from ..base_node import BaseNode
from ..base_tool import ToolBase
