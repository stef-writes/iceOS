"""Node configuration models for iceOS workflows.

This module defines the configuration models for different types of nodes
that can be used in iceOS workflows, including LLM operators, tools, conditions,
and nested chains.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    TypeAlias,
    Union,
)

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ice_core.models.enums import ModelProvider

# ruff: noqa: F811


# ---------------------------------------------------------------------------
# Forward-decl imports to avoid heavyweight runtime deps in typing-only mode
# ---------------------------------------------------------------------------

if TYPE_CHECKING:  # pragma: no cover – import only for type checkers
    from ice_sdk.interfaces.chain import ScriptChainLike as _ScriptChainLike
else:
    _ScriptChainLike = Any  # type: ignore[misc]

ScriptChainLike: TypeAlias = _ScriptChainLike  # public alias

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


# ---------------------------------------------------------------------------
# LLM configuration --------------------------------------------------------
# ---------------------------------------------------------------------------


class LLMConfig(BaseModel):
    """Provider-specific LLM configuration."""

    provider: ModelProvider = Field(..., description="LLM provider")
    api_key: Optional[str] = Field(None, description="API key (from env if None)")
    base_url: Optional[str] = Field(None, description="Custom base URL")
    timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")

    # Provider-specific settings
    openai_api_version: Optional[str] = Field(None, description="OpenAI API version")
    anthropic_version: Optional[str] = Field(None, description="Anthropic API version")

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Base node configuration --------------------------------------------------
# ---------------------------------------------------------------------------


class NodeMetadata(BaseModel):
    """Metadata for a node execution."""

    node_id: str
    node_type: str
    name: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class BaseNodeConfig(BaseModel):
    """Common fields shared by all node configurations."""

    id: str = Field(..., description="Unique identifier for the node")
    type: str = Field(..., description="Type discriminator (ai | tool | …)")
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
        node types (tool, agent, nested_chain, condition).  LLM nodes get a
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
                    "LLM node missing output_schema – defaulting to {'text':'string'} (will become a hard requirement in v2)",
                    DeprecationWarning,
                    stacklevel=2,
                )
            return  # No further checks for input_schema – prompts often vary.

        # Deterministic nodes – require both schemas ------------------------
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


class LLMOperatorConfig(BaseNodeConfig):
    """Configuration for an LLM-powered node.

    Historical note: early prototypes used the short discriminator value
    ``"ai"``.  This alias is now DEPRECATED – the canonical value going
    forward is ``"llm"``.  Runtime conversion still accepts the legacy
    string (see *node_conversion._NODE_TYPE_MAP*) but new blueprints MUST
    emit ``type="llm"``.
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

    tools: Optional[List[ToolConfig]] = Field(default=None)
    allowed_tools: Optional[List[str]] = Field(default=None)
    tool_args: Dict[str, Any] = Field(default_factory=dict)

    # Output formatting
    output_format: Optional[str] = Field(None, description="Expected output format")
    json_schema: Optional[Dict[str, Any]] = Field(
        None, description="JSON schema for output"
    )


class SkillNodeConfig(BaseNodeConfig):
    """Configuration for an idempotent tool execution."""

    type: Literal["tool"] = "tool"

    tool_name: str = Field(..., description="Registered name of the tool to invoke")
    tool_args: Dict[str, Any] = Field(default_factory=dict)


class ConditionNodeConfig(BaseNodeConfig):
    """Branching node that decides execution path based on *expression*."""

    type: Literal["condition"] = "condition"

    expression: str = Field(
        ..., description="Boolean expression evaluated against context"
    )
    true_branch: List[str] = Field(default_factory=list)
    false_branch: Optional[List[str]] = Field(default=None)


class NestedChainConfig(BaseNodeConfig):
    """Configuration for a *nested* ScriptChain."""

    type: Literal["nested_chain"] = "nested_chain"

    chain: "ScriptChainLike | Callable[[], ScriptChainLike]"  # type: ignore[name-defined]
    exposed_outputs: Dict[str, str] = Field(default_factory=dict)


class PrebuiltAgentConfig(BaseNodeConfig):
    """Configuration for using a pre-built multi-tool agent.

    Similar to :class:`LLMOperatorConfig` but encapsulates memory, multiple
    tool calls, iterative reasoning etc.  The historical discriminator was
    ``"prebuilt"`` – we now use ``"agent"`` across the board.
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

    @model_validator(mode="after")
    def _validate_attr(self) -> "PrebuiltAgentConfig":
        """Validate agent attribute configuration."""
        if not self.agent_attr:
            # Try to infer from package name
            package_parts = self.package.split(".")
            if package_parts:
                self.agent_attr = package_parts[-1]
        return self


# ---------------------------------------------------------------------------
# Discriminated union & helpers
# ---------------------------------------------------------------------------

NodeConfig = Annotated[
    Union[
        LLMOperatorConfig,
        SkillNodeConfig,
        ConditionNodeConfig,
        NestedChainConfig,
        PrebuiltAgentConfig,
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
