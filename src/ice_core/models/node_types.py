"""All node type definitions for iceOS."""
from enum import Enum
from ice_core.models import NodeType
from typing import Literal, List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .enums import NodeType

class RetryPolicy(BaseModel):
    """Declarative retry policy attached to any node."""
    max_attempts: int = Field(3, ge=1)
    backoff_strategy: Literal["fixed", "exponential"] = "exponential"
    backoff_seconds: float = Field(1.0, ge=0)

# Base configuration all nodes share
class BaseNodeConfig(BaseModel):
    """Common configuration for all nodes."""
    id: str = Field(..., description="Unique node identifier")
    type: NodeType = Field(..., description="Node type")
    name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = None
    
    # Execution control
    timeout_seconds: Optional[int] = Field(None, ge=1)
    retry_policy: Optional[RetryPolicy] = None
    
    # IO mappings
    input_mappings: Dict[str, str] = Field(default_factory=dict)
    output_mappings: Dict[str, str] = Field(default_factory=dict)
    
    # Dependencies
    depends_on: List[str] = Field(default_factory=list)

# Specific node configurations
class ToolNodeConfig(BaseNodeConfig):
    type: Literal[NodeType.TOOL] = NodeType.TOOL
    tool_ref: str = Field(..., description="Reference to registered tool")
    tool_args: Dict[str, Any] = Field(default_factory=dict)

class LLMNodeConfig(BaseNodeConfig):
    type: Literal[NodeType.LLM] = NodeType.LLM
    model: str = Field(..., description="Model identifier")
    prompt_template: str = Field(..., description="Prompt with {placeholders}")
    temperature: float = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, Any]] = None

class UnitNodeConfig(BaseNodeConfig):
    type: Literal[NodeType.UNIT] = NodeType.UNIT
    unit_ref: str = Field(..., description="Reference to registered unit")
    config_overrides: Dict[str, Any] = Field(default_factory=dict)

class AgentNodeConfig(BaseNodeConfig):
    type: Literal[NodeType.AGENT] = NodeType.AGENT
    agent_ref: str = Field(..., description="Reference to registered agent")
    tools: List[str] = Field(default_factory=list)
    max_iterations: int = Field(10, ge=1)
    memory_config: Optional[Dict[str, Any]] = None

class WorkflowNodeConfig(BaseNodeConfig):
    type: Literal[NodeType.WORKFLOW] = NodeType.WORKFLOW
    workflow_ref: str = Field(..., description="Reference to registered workflow")

class ConditionNodeConfig(BaseNodeConfig):
    type: Literal[NodeType.CONDITION] = NodeType.CONDITION
    expression: str = Field(..., description="Boolean expression")
    true_nodes: List[str] = Field(default_factory=list)
    false_nodes: List[str] = Field(default_factory=list)

class LoopNodeConfig(BaseNodeConfig):
    type: Literal[NodeType.LOOP] = NodeType.LOOP
    iterator_path: str = Field(..., description="Path to array in context")
    body_nodes: List[str] = Field(default_factory=list)
    max_iterations: int = Field(100, ge=1)

class ParallelNodeConfig(BaseNodeConfig):
    type: Literal[NodeType.PARALLEL] = NodeType.PARALLEL
    branches: List[List[str]] = Field(..., description="Parallel execution branches")
    wait_strategy: Literal["all", "any", "race"] = "all"

class CodeNodeConfig(BaseNodeConfig):
    type: Literal[NodeType.CODE] = NodeType.CODE
    code: str = Field(..., description="Python code to execute")
    runtime: Literal["python"] = "python"  # Future: support more

# Union type for all node configs
NodeConfig = ToolNodeConfig | LLMNodeConfig | UnitNodeConfig | AgentNodeConfig | WorkflowNodeConfig | ConditionNodeConfig | LoopNodeConfig | ParallelNodeConfig | CodeNodeConfig 