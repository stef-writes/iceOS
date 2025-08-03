"""Node models for workflow execution.

WHY THIS MODULE EXISTS:
- Provides Pydantic models for the MCP compiler tier (blueprint validation)
- These models represent the "blueprint" form that Frosty creates from natural language
- They get transformed into runtime objects by the orchestrator
- Intentionally separate from runtime classes to support incremental canvas building

Vision Context:
- MCP Tier: These models are used for blueprint validation and optimization
- Multi-granularity: Supports tool→node→chain→workflow progression
- Canvas: Enables partial blueprint construction with pending connections
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    TypeAlias,
    Union,
)

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ice_core.models.llm import LLMConfig
from ice_core.utils.vision_markers import mcp_tier, multi_granularity

# ---------------------------------------------------------------------------
# Retry policy --------------------------------------------------------------
# ---------------------------------------------------------------------------

class RetryPolicy(BaseModel):
    """Declarative retry policy attached to any node.

    Attributes
    ----------
    max_attempts : int
        Maximum number of attempts (including the first one).  Value **must** be
        ≥ 1.
    backoff_strategy : Literal["fixed", "linear", "exponential"]
        Algorithm used to calculate the wait time before the next retry.
    backoff_seconds : float
        Base seconds used by the strategy.  For *fixed* the wait time is
        exactly *backoff_seconds*, for *linear* it is `backoff_seconds * n`, and
        for *exponential* it is `backoff_seconds * 2**n` where *n* is the
        current attempt index (starting at 0).
    """

    max_attempts: int = Field(3, ge=1)
    backoff_strategy: Literal["fixed", "linear", "exponential"] = "exponential"
    backoff_seconds: float = Field(1.0, ge=0.0)

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from ice_core.models.enums import ModelProvider
from ice_core.models.node_metadata import NodeMetadata

# ruff: noqa: F811

# ---------------------------------------------------------------------------
# Forward-decl imports to avoid heavyweight runtime deps in typing-only mode
# ---------------------------------------------------------------------------

if TYPE_CHECKING:  # pragma: no cover – import only for type checkers
    from ice_core.protocols.workflow import WorkflowLike as _WorkflowLike
else:
    _WorkflowLike = Any  # type: ignore[misc]

WorkflowLike: TypeAlias = _WorkflowLike  # public alias
# Keep ScriptChainLike alias for backwards compatibility
ScriptChainLike: TypeAlias = _WorkflowLike

# ---------------------------------------------------------------------------
# Tool configuration --------------------------------------------------------
# ---------------------------------------------------------------------------

class ToolConfig(BaseModel):
    """Declarative description of a tool made available to an LLM agent."""

    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    required: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

# ---------------------------------------------------------------------------
# Context handling ---------------------------------------------------------
# ---------------------------------------------------------------------------

class ContextFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    CODE = "code"
    CUSTOM = "custom"

class InputMapping(BaseModel):
    """Mapping configuration for node inputs."""

    source_node_id: str = Field(
        ..., description="Source node ID (UUID of the dependency)"
    )
    source_output_key: str = Field(
        ...,
        description="Key from the source node's output object to use (e.g. 'text', 'result', 'data.items.0')",
    )
    rules: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional transformation rules (e.g. 'truncate', 'format')",
    )

class ContextRule(BaseModel):
    """Rule for handling context in a node."""

    include: bool = Field(default=True, description="Whether to include this context")
    format: ContextFormat = Field(
        default=ContextFormat.TEXT, description="Format of the context"
    )
    required: bool = Field(
        default=False, description="Whether this context is required"
    )
    max_tokens: Optional[int] = Field(
        None, description="Maximum tokens allowed for this context"
    )
    truncate: bool = Field(
        default=True, description="Whether to truncate if context exceeds max_tokens"
    )

# LLMConfig now imported from ice_core.models.llm for consistency

# ---------------------------------------------------------------------------
# Base node configuration --------------------------------------------------
# ---------------------------------------------------------------------------

# NodeMetadata moved to node_metadata.py

@mcp_tier("Base blueprint configuration for all node types")
class BaseNodeConfig(BaseModel):
    """Base configuration for all nodes - blueprint representation.
    
    WHY: This is the "design-time" representation that can be validated
    without executing. Supports incremental canvas construction where
    users can add nodes before all connections are defined.
    """

    id: str = Field(..., description="Unique identifier for the node")
    type: str = Field(..., description="Type discriminator (tool | llm | agent | ...)")
    name: Optional[str] = Field(None, description="Human-readable name")
    dependencies: List[str] = Field(
        default_factory=list, description="IDs of prerequisite nodes"
    )
    level: int = Field(default=0, description="Execution level for parallelism")
    metadata: Optional[NodeMetadata] = None
    provider: ModelProvider = Field(
        default=ModelProvider.OPENAI, description="Model provider for the node"
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        description="Hard timeout for node execution in seconds (None = no timeout)",
    )
    retries: int = Field(
        default=0,
        ge=0,
        description="Maximum number of retries if the node execution fails",
    )
    backoff_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Base backoff seconds for exponential retry backoff (0 disables)",
    )

    # New declarative retry policy (preferred over *retries* + *backoff_seconds*)
    retry_policy: Optional[RetryPolicy] = Field(
        default=None,
        description="Structured retry policy (overrides 'retries' & 'backoff_seconds' when provided)",
    )

    # IO schemas – can be either a JSON-serialisable dict *or* a Pydantic model
    input_schema: Union[Dict[str, Any], Type[BaseModel]] = Field(default_factory=dict)
    output_schema: Union[Dict[str, Any], Type[BaseModel]] = Field(default_factory=dict)

    input_mappings: Dict[str, InputMapping] = Field(default_factory=dict)
    output_mappings: Dict[str, str] = Field(default_factory=dict)

    use_cache: bool = Field(
        default=True,
        description="Whether the orchestrator should reuse cached results when the context & config are unchanged.",
    )

    input_selection: Optional[List[str]] = Field(
        None, description="List of input keys to include (None = all)"
    )
    output_selection: Optional[List[str]] = Field(
        None, description="List of output keys to include (None = all)"
    )

    # Context rules for this node
    context_rules: Dict[str, ContextRule] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("dependencies")
    @classmethod
    def _no_self_dependency(cls, v: List[str], info: Any) -> List[str]:
        """Ensure node doesn't depend on itself."""
        node_id = info.data.get("id") if info.data else None
        if node_id and node_id in v:
            raise ValueError(f"Node '{node_id}' cannot depend on itself")
        return v

    @model_validator(mode="after")
    def _ensure_metadata(self) -> "BaseNodeConfig":
        """Ensure metadata is populated with node info."""
        if self.metadata is None:
            self.metadata = NodeMetadata(
                node_id=self.id,
                node_type=self.type,
                name=self.name,
                start_time=datetime.utcnow(),
            )
        return self

    def runtime_validate(self) -> None:  # – override in subclasses
        """Validate configuration at runtime.

        Enforces mandatory *input_schema* and *output_schema* for deterministic
        node types (tool, agent, condition).  LLM nodes get a
        fallback ``{"text": "string"}`` output schema if none is provided so
        experimentation remains low-friction.
        """

        import warnings  # local import to avoid top-level dependency when unused

        # Canonical discriminator is guaranteed by Pydantic Literal typing but
        # we cast to *str* defensively for forward-compat.
        node_type: str = str(self.type)

        # Helper – detect “missing” schema (empty dict / None)
        def _is_schema_missing(schema: Any) -> bool:  # noqa: ANN401 – generic
            if schema is None:
                return True
            if isinstance(schema, dict):
                return len(schema) == 0
            # Pydantic model class present → not missing
            return False

        if node_type == "llm":
            # Provide soft fallback so authors aren’t forced to specify schema
            if _is_schema_missing(self.output_schema):
                self.output_schema = {"text": "string"}  # type: ignore[assignment]
                warnings.warn(
                    "LLM node missing output_schema – defaulting to {'text':'string'}",
                    UserWarning,
                    stacklevel=2,
                )
            return  # No further checks for input_schema – prompts often vary.

        # Node types that don't require schema validation
        schema_optional_types = {"workflow", "loop", "parallel", "code", "human", "monitor", "swarm"}
        
        if node_type in schema_optional_types:
            return

        # Deterministic execution nodes – require both schemas ------------------------
        if _is_schema_missing(self.input_schema) or _is_schema_missing(self.output_schema):
            raise ValueError(
                f"Node '{self.id}' of type '{node_type}' must declare non-empty input_schema and output_schema."
            )

        # Validate literals inside *dict*-style schemas --------------------
        from ice_core.utils.schema import is_valid_schema_dict  # local import

        for field_name, schema_val in [
            ("input_schema", self.input_schema),
            ("output_schema", self.output_schema),
        ]:
            if isinstance(schema_val, dict):
                ok, errs = is_valid_schema_dict(schema_val)
                if not ok:
                    joined = "; ".join(errs)
                    raise ValueError(
                        f"Node '{self.id}' has invalid {field_name}: {joined}"
                    )

    @staticmethod
    def is_pydantic_schema(schema: Any) -> bool:
        """Check if schema is a Pydantic model."""
        return isinstance(schema, type) and issubclass(schema, BaseModel)

# ---------------------------------------------------------------------------
# Specific node configurations ----------------------------------------------
# ---------------------------------------------------------------------------

@mcp_tier("Blueprint for LLM text operations")  
@multi_granularity("node")
class LLMOperatorConfig(BaseNodeConfig):
    """LLM operator configuration - Pure text generation without tools.
    
    WHY: For stateless, one-shot LLM operations. NO tool access.
    If you need tools, use AgentNodeConfig instead.
    
    Use this for: Summarization, extraction, translation, single Q&A
    Use AgentNodeConfig for: Any LLM operation that needs tools or memory
    
    In Frosty: "summarize in 3 bullets" → LLMOperatorConfig with template
    """

    type: Literal["llm"] = "llm"  # discriminator

    model: str = Field(..., description="Model name, e.g. gpt-3.5-turbo")
    prompt: str = Field(..., description="Prompt template")
    llm_config: LLMConfig = Field(..., description="Provider-specific parameters")

    temperature: float = 0.7
    max_tokens: Optional[int] = None

    context_rules: Dict[str, ContextRule] = Field(default_factory=dict)
    format_specifications: Dict[str, Any] = Field(default_factory=dict)
    coerce_output_types: bool = Field(default=True)
    coerce_input_types: bool = Field(default=True)

    # NOTE: Tools removed - use AgentNodeConfig for LLM + tools
    # LLM nodes are for pure text generation only

    # Output formatting
    output_format: Optional[str] = Field(None, description="Expected output format")
    json_schema: Optional[Dict[str, Any]] = Field(
        None, description="JSON schema for output"
    )

@mcp_tier("Blueprint for simple function execution")
@multi_granularity("tool")
class ToolNodeConfig(BaseNodeConfig):
    """Configuration for tool nodes - atomic utilities.
    
    WHY: Represents the simplest granularity - a single tool invocation.
    In Frosty: "parse this CSV" → ToolNodeConfig(tool_name="csv_reader")
    """

    type: Literal["tool"] = "tool"

    tool_name: str = Field(..., description="Registered name of the tool to invoke")
    tool_args: Dict[str, Any] = Field(default_factory=dict)

@mcp_tier("Blueprint for intelligent decision-making")
@multi_granularity("chain")  
class AgentNodeConfig(BaseNodeConfig):
    """Agent configuration - Multi-turn reasoning with memory and state.
    
    WHY: Agents maintain conversation history, learn from interactions,
    and can perform complex multi-step reasoning. They have persistent
    memory across turns, unlike stateless LLM nodes.
    
    Use this for: Customer support, research tasks, iterative problem solving
    Use LLMOperatorConfig for: Single-shot generation without memory needs
    
    In Frosty: "help me debug this issue" → AgentNodeConfig with memory
    """

    type: Literal["agent"] = "agent"  # canonical

    package: str = Field(
        ..., description="Import path or installed package exposing the agent"
    )
    agent_attr: Optional[str] = Field(None)
    model: Optional[str] = Field(None)
    version_constraint: Optional[str] = Field(None)

    # Agent-specific configuration
    agent_config: Dict[str, Any] = Field(default_factory=dict)
    tools: Optional[List[ToolConfig]] = Field(default=None)
    memory: Optional[Dict[str, Any]] = Field(default=None)
    max_iterations: int = Field(
        default=10,
        description="Maximum agent reasoning iterations to prevent infinite loops"
    )
    
    # LLM configuration for the agent's reasoning
    llm_config: Optional[LLMConfig] = Field(
        default=None,
        description="LLM configuration for agent reasoning. If None, uses defaults."
    )

    @model_validator(mode="after")
    def _validate_attr(self) -> "AgentNodeConfig":
        """Validate agent attribute configuration."""
        if not self.agent_attr:
            # Try to infer from package name
            package_parts = self.package.split(".")
            if package_parts:
                self.agent_attr = package_parts[-1]
        return self

class ConditionNodeConfig(BaseNodeConfig):
    """Branching node that decides execution path based on *expression*."""

    type: Literal["condition"] = "condition"

    expression: str = Field(
        ..., description="Boolean expression evaluated against context"
    )
    true_branch: List[str] = Field(default_factory=list)
    false_branch: Optional[List[str]] = Field(default=None)

@mcp_tier("Blueprint for embedded workflows")
@multi_granularity("workflow")
class WorkflowNodeConfig(BaseNodeConfig):
    """Configuration for embedding a sub-workflow.
    
    WHY: Enables composition of workflows. Replaces both Unit and NestedChain
    concepts with a single, clear abstraction for workflow embedding.
    
    Use this for: Reusable workflow components, modular design
    """

    type: Literal["workflow"] = "workflow"

    workflow_ref: str = Field(..., description="Reference to registered workflow")
    exposed_outputs: Dict[str, str] = Field(default_factory=dict)
    config_overrides: Dict[str, Any] = Field(
        default_factory=dict,
        description="Override configuration for the embedded workflow"
    )

@mcp_tier("Blueprint for iteration")
class LoopNodeConfig(BaseNodeConfig):
    """Configuration for loop/iteration nodes.
    
    WHY: Enables iteration over collections with proper context propagation.
    
    Use this for: Processing lists, batch operations, map-reduce patterns
    """

    type: Literal["loop"] = "loop"

    items_source: str = Field(..., description="Context key containing items to iterate over")
    item_var: str = Field(default="item", description="Variable name for current item")
    body_nodes: List[str] = Field(..., description="Node IDs to execute for each item")
    max_iterations: Optional[int] = Field(None, description="Maximum iterations allowed")
    parallel: bool = Field(default=False, description="Execute iterations in parallel")

@mcp_tier("Blueprint for parallel execution")
class ParallelNodeConfig(BaseNodeConfig):
    """Configuration for parallel execution branches.
    
    WHY: Enables concurrent execution of independent branches.
    
    Use this for: Independent operations, performance optimization
    """

    type: Literal["parallel"] = "parallel"

    branches: List[List[str]] = Field(
        ...,
        description="List of branches, each containing node IDs to execute"
    )
    max_concurrency: Optional[int] = Field(
        None,
        description="Maximum concurrent branches (None = unlimited)"
    )
    merge_outputs: bool = Field(
        default=True,
        description="Whether to merge outputs from all branches"
    )

@mcp_tier("Blueprint for recursive agent conversations")
@multi_granularity("chain")
class RecursiveNodeConfig(BaseNodeConfig):
    """Configuration for recursive/cyclic execution.
    
    WHY: Enables agents to loop back and continue conversations until convergence.
    Leverages existing memory systems and state management for sophisticated
    recursive workflows while maintaining safety through convergence conditions.
    
    Use this for: Agent negotiations, iterative refinement, multi-turn conversations
    """

    type: Literal["recursive"] = "recursive"

    # Which nodes can loop back to this one (creates controlled cycles)
    recursive_sources: List[str] = Field(
        default_factory=list,
        description="Node IDs that can trigger recursive execution back to this node"
    )
    
    # Convergence conditions (leverages existing condition system)
    convergence_condition: Optional[str] = Field(
        None,
        description="Expression that stops recursion when true (e.g. 'agreement_reached == True')"
    )
    max_iterations: int = Field(
        default=50,
        description="Safety limit to prevent infinite loops"
    )
    
    # Agent/workflow configuration (one of these must be specified)
    agent_package: Optional[str] = Field(
        None,
        description="Import path for agent to execute in recursive loop"
    )
    workflow_ref: Optional[str] = Field(
        None,
        description="Reference to workflow to execute in recursive loop"
    )
    
    # Memory and context settings
    preserve_context: bool = Field(
        default=True,
        description="Whether to preserve context across recursive iterations"
    )
    context_key: str = Field(
        default="recursive_context",
        description="Key for storing recursive context in state"
    )

    @model_validator(mode="after")
    def _validate_recursive_config(self) -> "RecursiveNodeConfig":
        """Validate recursive node configuration."""
        if not self.agent_package and not self.workflow_ref:
            raise ValueError("RecursiveNodeConfig must specify either agent_package or workflow_ref")
        
        if self.agent_package and self.workflow_ref:
            raise ValueError("RecursiveNodeConfig cannot specify both agent_package and workflow_ref")
        
        if not self.recursive_sources:
            raise ValueError("RecursiveNodeConfig must specify at least one recursive_source")
        
        return self

@mcp_tier("Blueprint for code execution")
class CodeNodeConfig(BaseNodeConfig):
    """Configuration for direct code execution.
    
    WHY: Enables custom logic that doesn't fit other node types.
    
    Use this for: Data transformations, custom calculations, glue code
    """

    type: Literal["code"] = "code"

    language: Literal["python", "javascript"] = Field(
        default="python",
        description="Programming language"
    )
    code: str = Field(..., description="Code to execute")
    sandbox: bool = Field(
        default=True,
        description="Execute in sandboxed environment"
    )
    imports: List[str] = Field(
        default_factory=list,
        description="Allowed imports for sandboxed execution"
    )

# ---------------------------------------------------------------------------
# Discriminated union & helpers
# ---------------------------------------------------------------------------

NodeConfig = Annotated[
    Union[
        ToolNodeConfig,
        LLMOperatorConfig,
        AgentNodeConfig,
        ConditionNodeConfig,
        WorkflowNodeConfig,
        LoopNodeConfig,
        ParallelNodeConfig,
        RecursiveNodeConfig,
        CodeNodeConfig,
    ],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Execution results -------------------------------------------------------
# ---------------------------------------------------------------------------

class NodeExecutionRecord(BaseModel):
    """Record of node execution statistics."""

    node_id: str
    executions: int = Field(0, ge=0)
    successes: int = Field(0, ge=0)
    failures: int = Field(0, ge=0)
    avg_duration: float = Field(0.0, ge=0)
    last_executed: Optional[datetime] = None
    token_usage: Dict[str, int] = Field(default_factory=dict)
    provider_usage: Dict[str, Dict[str, int]] = Field(default_factory=dict)

class NodeIO(BaseModel):
    """Input/output schema for a node."""

    data_schema: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)

class UsageMetadata(BaseModel):
    """Token usage and cost metadata."""

    prompt_tokens: int = Field(0, ge=0)
    completion_tokens: int = Field(0, ge=0)
    total_tokens: int = Field(0, ge=0)
    cost: float = Field(0.0, ge=0)
    api_calls: int = Field(1, ge=1)
    model: str
    node_id: str
    provider: ModelProvider
    token_limits: Dict[str, int] = Field(
        default_factory=lambda: {"context": 4096, "completion": 1024}
    )

    @model_validator(mode="after")
    def _autofill_totals(self) -> "UsageMetadata":
        if self.total_tokens == 0 and (self.prompt_tokens or self.completion_tokens):
            self.total_tokens = self.prompt_tokens + self.completion_tokens
        return self

class NodeExecutionResult(BaseModel):
    """Result of a node execution."""

    success: bool = True
    error: Optional[str] = None
    output: Optional[Any] = Field(None, json_schema_extra={"coerce": True})
    metadata: NodeMetadata
    usage: Optional[UsageMetadata] = None
    execution_time: Optional[float] = None
    context_used: Optional[Dict[str, Any]] = None
    token_stats: Optional[Dict[str, Any]] = None
    budget_status: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

class ChainExecutionResult(BaseModel):
    """Result of a chain execution."""

    success: bool = True
    error: Optional[str] = None
    output: Optional[Any] = None
    metadata: NodeMetadata
    chain_metadata: Optional["ChainMetadata"] = None
    execution_time: Optional[float] = None
    token_stats: Optional[Dict[str, Any]] = None

class ChainMetadata(BaseModel):
    """Metadata for a chain execution."""

    chain_id: str
    name: str
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str
    node_count: int = Field(ge=1)
    edge_count: int = Field(ge=0)
    topology_hash: str
    tags: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)

try:
    ChainExecutionResult.model_rebuild()
except NameError:
    pass

# ---------------------------------------------------------------------------
# Serializable ChainSpec (v1)
# ---------------------------------------------------------------------------

class ChainSpec(BaseModel):
    """Serializable chain specification."""

    api_version: str = Field("chain.v1", frozen=True)
    metadata: Dict[str, Any] = Field(default_factory=lambda: {"version": "1.0.0"})
    nodes: List[NodeConfig] = Field(min_length=1)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "api_version": "chain.v1",
                    "metadata": {"name": "demo-chain"},
                    "nodes": [{"id": "start", "type": "system.log"}],
                }
            ]
        },
    )

# ---------------------------------------------------------------------------
# Phase-2 execution-control node configs (Swarm / Human / Monitor)
# ---------------------------------------------------------------------------

class AgentSpec(BaseModel):
    """Specification for an agent inside a swarm."""

    package: str
    role: str
    config_overrides: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


@mcp_tier("Multi-agent swarm coordination")
@multi_granularity("chain")
class SwarmNodeConfig(BaseNodeConfig):
    """Configuration for a multi-agent swarm node."""

    type: Literal["swarm"] = "swarm"

    agents: List[AgentSpec] = Field(..., min_length=2)
    coordination_strategy: Literal["consensus", "hierarchical", "marketplace"] = "consensus"
    max_rounds: int = Field(10, ge=1)
    consensus_threshold: float = Field(0.75, ge=0.5, le=1.0)

    def runtime_validate(self) -> None:  # noqa: D401 – override
        super().runtime_validate()

        if len(self.agents) < 2:
            raise ValueError("Swarm requires at least 2 agents")

        # ensure non-empty packages and unique roles
        roles = []
        for agent in self.agents:
            if not agent.package.strip():
                raise ValueError("Agent package cannot be empty")
            if not agent.role.strip():
                raise ValueError("Agent role cannot be empty")
            roles.append(agent.role)
        if len(set(roles)) != len(roles):
            raise ValueError("Swarm agents must have unique roles")


@mcp_tier("Human-in-the-loop workflows")
@multi_granularity("node")
class HumanNodeConfig(BaseNodeConfig):
    """Human approval / input node."""

    type: Literal["human"] = "human"

    prompt_message: str = Field(..., min_length=1)
    approval_type: Literal["approve_reject", "input_required", "choice"] = "approve_reject"
    timeout_seconds: Optional[int] = Field(None, ge=1)
    auto_approve_after: Optional[int] = Field(None, ge=1)
    choices: Optional[List[str]] = None
    escalation_path: Optional[str] = Field(None, description="Path for escalation if timeout occurs")

    def runtime_validate(self) -> None:
        super().runtime_validate()
        if not self.prompt_message.strip():
            raise ValueError("Human node requires non-empty prompt_message")
        if self.approval_type == "choice" and (not self.choices or len(self.choices) < 2):
            raise ValueError("Choice approval type requires at least 2 choices")
        if self.auto_approve_after and not self.timeout_seconds:
            raise ValueError("auto_approve_after requires timeout_seconds")
        if self.auto_approve_after and self.timeout_seconds and self.auto_approve_after >= self.timeout_seconds:
            raise ValueError("auto_approve_after must be less than timeout_seconds")


@mcp_tier("Real-time workflow monitoring")
@multi_granularity("node")
class MonitorNodeConfig(BaseNodeConfig):
    """Monitor node that watches a metric expression and triggers actions."""

    type: Literal["monitor"] = "monitor"

    metric_expression: str = Field(..., min_length=1)
    action_on_trigger: Literal["alert_only", "pause", "abort"] = "alert_only"
    alert_channels: List[str] = Field(default_factory=list)
    check_interval_seconds: int = Field(5, ge=1)

    def runtime_validate(self) -> None:
        super().runtime_validate()
        if not self.metric_expression.strip():
            raise ValueError("Monitor node requires non-empty metric_expression")
        # basic expression syntax check
        try:
            compile(self.metric_expression, "<monitor>", "eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid metric expression syntax: {e}")
        valid_channels = {"email", "slack", "webhook", "sms", "dashboard"}
        invalid = set(self.alert_channels) - valid_channels
        if invalid:
            raise ValueError(f"Invalid alert channels: {invalid}")


# ---------------------------------------------------------------------------
# Type aliases for backward compatibility
# ---------------------------------------------------------------------------

NodeConfig = Union[
    ToolNodeConfig,
    LLMOperatorConfig,
    AgentNodeConfig,
    ConditionNodeConfig,
    WorkflowNodeConfig,
    LoopNodeConfig,
    ParallelNodeConfig,
    RecursiveNodeConfig,
    CodeNodeConfig,
    HumanNodeConfig,
    MonitorNodeConfig,
    SwarmNodeConfig,
]

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__: list[str] = [
    "RetryPolicy",
    "ToolConfig",
    "ContextFormat",
    "InputMapping",
    "ContextRule",
    "BaseNodeConfig",
    "LLMOperatorConfig",
    "ToolNodeConfig",
    "AgentNodeConfig",
    "ConditionNodeConfig",
    "WorkflowNodeConfig",
    "LoopNodeConfig",
    "ParallelNodeConfig",
    "RecursiveNodeConfig",
    "CodeNodeConfig",
    "HumanNodeConfig",
    "MonitorNodeConfig",
    "SwarmNodeConfig",
    "AgentSpec",
    "NodeExecutionRecord",
    "NodeIO",
    "UsageMetadata",
    "NodeExecutionResult",
    "ChainExecutionResult",
    "ChainMetadata",
    "ChainSpec",
    "NodeConfig",
    "NodeMetadata",  # Re-export from node_metadata module
]
