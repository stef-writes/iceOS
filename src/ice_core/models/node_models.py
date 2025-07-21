from __future__ import annotations

"""Node configuration and execution models (moved from *ice_sdk.models*).

This module defines the canonical Pydantic models used by *ice_core*,
*ice_sdk* and *ice_orchestrator* for describing workflow nodes and their
execution metadata.

It deliberately lives in the **core** layer so both higher-level layers can
import it **without** creating circular or upward dependencies (Cursor rule
#4).
"""

# NOTE: The original implementation lived in ``ice_sdk.models.node_models``.
#       This is a verbatim copy with only the following adjustments:
#       • Internal imports now reference *ice_core.models* siblings
#       • All deprecation/compat-shims have been removed
#       • File is fully mypy --strict compliant

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

from .enums import ModelProvider
from .llm import LLMConfig
from .node_metadata import NodeMetadata

# ---------------------------------------------------------------------------
# Forward-decl imports to avoid heavyweight runtime deps in typing-only mode
# ---------------------------------------------------------------------------

if TYPE_CHECKING:  # pragma: no cover – import only for type checkers
    from ice_sdk.interfaces.chain import ScriptChainLike as _ScriptChainLike
else:
    _ScriptChainLike = Any  # type: ignore[misc]

ScriptChainLike: TypeAlias = _ScriptChainLike  # public alias

# ---------------------------------------------------------------------------
# Supporting value objects
# ---------------------------------------------------------------------------


class ToolConfig(BaseModel):
    """Declarative description of a tool made available to an LLM agent."""

    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]


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
        ..., description="Key from the source node's output object to use (e.g. 'text', 'result', 'data.items.0')",
    )
    rules: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional mapping/transformation rules (currently unused)",
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
        default=True, description="Whether to truncate if over token limit"
    )


# ---------------------------------------------------------------------------
# Base node configuration
# ---------------------------------------------------------------------------


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
        default=None,
        description="Ordered list of input keys to include in the prompt. None = include all.",
    )

    # ------------------------------------------------------------------
    # Validators & helpers
    # ------------------------------------------------------------------

    @field_validator("dependencies")
    @classmethod
    def _no_self_dependency(cls, v: List[str], info: Any) -> List[str]:  # noqa: D401
        node_id = info.data.get("id")
        if node_id and node_id in v:
            raise ValueError(f"Node {node_id} cannot depend on itself")
        return v

    @model_validator(mode="after")
    def _ensure_metadata(self) -> "BaseNodeConfig":  # noqa: D401
        if self.metadata is None:
            self.metadata = NodeMetadata(  # type: ignore[call-arg]
                node_id=self.id,
                node_type=self.type,
                version="1.0.0",
                description=f"Node {self.id} (type={self.type})",
                tags=["auto"],
            )
        return self

    # -- runtime hooks -------------------------------------------------------

    def runtime_validate(self) -> None:  # noqa: D401 – override in subclasses
        """Idempotent runtime validation hook (no-op by default)."""
        return None

    # Static helpers ---------------------------------------------------------

    @staticmethod
    def is_pydantic_schema(schema: Any) -> bool:  # noqa: D401
        from pydantic import BaseModel as _BaseModelChecker

        return isinstance(schema, type) and issubclass(schema, _BaseModelChecker)


# ---------------------------------------------------------------------------
# Concrete node types
# ---------------------------------------------------------------------------


class LLMOperatorConfig(BaseNodeConfig):
    """Configuration for an LLM-powered node."""

    type: Literal["ai", "llm"] = "llm"  # discriminator

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


class SkillNodeConfig(BaseNodeConfig):
    """Configuration for an idempotent tool execution."""

    type: Literal["tool", "skill"] = "skill"

    tool_name: str = Field(..., description="Registered name of the tool to invoke")
    tool_args: Dict[str, Any] = Field(default_factory=dict)


class ConditionNodeConfig(BaseNodeConfig):
    """Branching node that decides execution path based on *expression*."""

    type: Literal["condition"] = "condition"

    expression: str = Field(..., description="Boolean expression evaluated against context")
    true_branch: List[str] = Field(default_factory=list)
    false_branch: Optional[List[str]] = Field(default=None)


class NestedChainConfig(BaseNodeConfig):
    """Configuration for a *nested* ScriptChain."""

    type: Literal["nested_chain"] = "nested_chain"

    chain: "ScriptChainLike | Callable[[], ScriptChainLike]"  # type: ignore[name-defined]
    exposed_outputs: Dict[str, str] = Field(default_factory=dict)


class PrebuiltAgentConfig(BaseNodeConfig):
    """Configuration for using a pre-built third-party agent."""

    type: Literal["prebuilt"] = "prebuilt"

    package: str = Field(..., description="Import path or installed package exposing the agent")
    agent_attr: Optional[str] = Field(None)
    model: Optional[str] = Field(None)
    version_constraint: Optional[str] = Field(None)

    @model_validator(mode="after")
    def _validate_attr(self) -> "PrebuiltAgentConfig":  # noqa: D401
        if ":" in self.package and self.agent_attr is None:
            self.package, self.agent_attr = self.package.split(":", 1)
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
# Execution metadata
# ---------------------------------------------------------------------------


class NodeExecutionRecord(BaseModel):
    node_id: str
    executions: int = Field(0, ge=0)
    successes: int = Field(0, ge=0)
    failures: int = Field(0, ge=0)
    avg_duration: float = Field(0.0, ge=0)
    last_executed: Optional[datetime] = None
    token_usage: Dict[str, int] = Field(default_factory=dict)
    provider_usage: Dict[str, Dict[str, int]] = Field(default_factory=dict)


class NodeIO(BaseModel):
    data_schema: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class UsageMetadata(BaseModel):
    prompt_tokens: int = Field(0, ge=0)
    completion_tokens: int = Field(0, ge=0)
    total_tokens: int = Field(0, ge=0)
    cost: float = Field(0.0, ge=0)
    api_calls: int = Field(1, ge=1)
    model: str
    node_id: str
    provider: ModelProvider
    token_limits: Dict[str, int] = Field(default_factory=lambda: {"context": 4096, "completion": 1024})

    @model_validator(mode="after")
    def _autofill_totals(self) -> "UsageMetadata":  # noqa: D401
        if self.total_tokens == 0 and (self.prompt_tokens or self.completion_tokens):
            self.total_tokens = self.prompt_tokens + self.completion_tokens
        return self


class NodeExecutionResult(BaseModel):
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
    success: bool = True
    error: Optional[str] = None
    output: Optional[Any] = None
    metadata: NodeMetadata
    chain_metadata: Optional["ChainMetadata"] = None
    execution_time: Optional[float] = None
    token_stats: Optional[Dict[str, Any]] = None


class ChainMetadata(BaseModel):
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
# Stubs required by tests – kept as dataclasses to minimise dep-surface
# ---------------------------------------------------------------------------

from dataclasses import dataclass


@dataclass(slots=True)
class LoopNodeConfig:  # noqa: D101 – test stub
    id: str
    items: Optional[List[int]] = None
    iteration_key: Optional[str] = None


@dataclass(slots=True)
class EvaluatorNodeConfig:  # noqa: D101 – test stub
    id: str
    reference: str
    threshold: float = 0.5


# ---------------------------------------------------------------------------
# Serializable ChainSpec (v1)
# ---------------------------------------------------------------------------

class ChainSpec(BaseModel):
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
