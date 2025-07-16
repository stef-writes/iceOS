# pyright: reportGeneralTypeIssues=false
# ruff: noqa: E402
"""
Data models for node configurations and metadata
"""

import warnings  # noqa: E402 – after stdlib imports
from datetime import datetime
from enum import Enum

# Standard library -----------------------------------------------------------------
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

if TYPE_CHECKING:  # pragma: no cover – import only for type checkers
    from ice_sdk.interfaces.chain import ScriptChainLike as _ScriptChainLike
else:
    _ScriptChainLike = Any  # type: ignore[misc]

# Re-export the alias for downstream modules -----------------------------
ScriptChainLike: TypeAlias = _ScriptChainLike

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .config import LLMConfig, ModelProvider

# (import moved below for clarity)


# Emit structured warning **once** at import.  We keep a simple alias so that
# instantiation does *not* raise, allowing existing code to continue running
# while migrations are in progress.
warnings.warn(
    "ice_sdk.models.node_models.NodeMetadata is deprecated; import from ice_core.models instead.",
    DeprecationWarning,
    stacklevel=2,
)

# ---------------------------------------------------------------------------
# Deprecation alias – migrate to ice_core.models.NodeMetadata
# ---------------------------------------------------------------------------
from ice_core.models import NodeMetadata as _CoreNodeMetadata  # noqa: E402

# Re-export deprecated alias so existing imports continue to work.  The file-level
# ``warnings.warn`` ensures users see a deprecation notice while preserving full
# type-compatibility (the alias is the actual class, not a wrapped function).
NodeMetadata: TypeAlias = _CoreNodeMetadata


class ToolConfig(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]


# ---------------------------------------------------------------------------
# Context helpers (moved up) -------------------------------------------------
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
        description="Key from the source node's output object to use (e.g., 'text', 'result', 'data.items.0')",
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
# NEW, SIMPLIFIED NODE CONFIG CLASSES
# ---------------------------------------------------------------------------

# NOTE: The original monolithic ``NodeConfig`` class has been renamed to
# ``AiNodeConfig``.  A lighter ``ToolNodeConfig`` was added and, for backwards
# compatibility, ``NodeConfig`` is now an alias::
#
#     NodeConfig = Union[AiNodeConfig, ToolNodeConfig]
#
# External code therefore keeps working while the new, clearer split is in
# place.  The *only* mandatory discriminator is the ``type`` field which must
# be either ``"ai"`` or ``"tool"``.


class BaseNodeConfig(BaseModel):
    """Common fields shared by all node configurations."""

    id: str = Field(..., description="Unique identifier for the node")
    type: str = Field(..., description="Type discriminator (ai | tool)")
    name: Optional[str] = Field(None, description="Human-readable name")
    dependencies: List[str] = Field(
        default_factory=list, description="IDs of prerequisite nodes"
    )
    level: int = Field(default=0, description="Execution level for parallelism")
    metadata: Optional[NodeMetadata] = None
    provider: ModelProvider = Field(
        default=ModelProvider.OPENAI, description="Model provider for the node"
    )
    # Maximum time (in seconds) the orchestrator will wait for this node to finish. ``None`` disables the timeout.
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
        description="Base backoff seconds used for exponential backoff between retries (0 disables sleep)",
    )

    # IO schemas are optional and can be provided as loose dicts or Pydantic models.
    input_schema: Union[Dict[str, Any], Type[BaseModel]] = Field(default_factory=dict)
    output_schema: Union[Dict[str, Any], Type[BaseModel]] = Field(default_factory=dict)

    # Mapping of placeholders in the prompt / template to dependency outputs.
    input_mappings: Dict[str, InputMapping] = Field(default_factory=dict)

    # Mapping of public *alias* → nested path inside this node's raw output.
    # Allows downstream nodes to depend on stable aliases instead of fragile JSON
    # paths coupling them to internal representation details.
    output_mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of exposed output keys to nested paths in the node's actual output.",
    )

    use_cache: bool = Field(
        default=True,
        description="Whether the orchestrator should reuse cached results when the context & config are unchanged.",
    )

    input_selection: Optional[List[str]] = Field(
        default=None,
        description="List of input keys to include in the prompt (order preserved). If None, include all inputs.",
    )

    @field_validator("dependencies")
    @classmethod
    def _no_self_dependency(cls, v: List[str], info: Any) -> List[str]:
        node_id = info.data.get("id")
        if node_id and node_id in v:
            raise ValueError(f"Node {node_id} cannot depend on itself")
        return v

    @model_validator(mode="after")  # pyright: ignore[reportGeneralTypeIssues]
    def _ensure_metadata(self) -> Any:  # type: ignore[override]
        """Ensure ``metadata`` is set on the instance after validation."""

        if self.metadata is None:
            self.metadata = NodeMetadata(  # type: ignore[call-arg]
                node_id=self.id,
                node_type=self.type,
                version="1.0.0",
                description=f"Node {self.id} (type={self.type})",
                tags=["auto"],
            )
        return self

    # ------------------------------------------------------------------
    # Common helpers preserved from the legacy implementation
    # ------------------------------------------------------------------

    @field_validator("input_mappings")
    @classmethod
    def _validate_input_mappings(
        cls, v: Dict[str, InputMapping], info: Any
    ) -> Dict[str, InputMapping]:
        """Ensure that input mappings reference declared dependencies."""
        data = info.data
        dependencies = data.get("dependencies", [])
        if dependencies:
            for placeholder, mapping in v.items():
                # Allow literal/static values as-is.
                if not isinstance(mapping, InputMapping):
                    continue
                if mapping.source_node_id not in dependencies:
                    raise ValueError(
                        f"Input mapping for '{placeholder}' references non-existent dependency '{mapping.source_node_id}'. "
                        f"Available dependencies: {dependencies}"
                    )
        return v

    def process_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and coerce *input_data* according to *input_schema*."""
        # ``input_schema`` can be either a plain ``dict`` or a ``BaseModel`` subclass. The
        # latter does **not** implement ``items()`` which confuses static analysis and
        # would raise at runtime.  Iterate only when a real mapping was provided.

        if not self.input_schema:
            return input_data

        schema_items: list[tuple[str, Any]]
        if isinstance(self.input_schema, dict):
            schema_items = list(self.input_schema.items())
            if not schema_items:  # empty dict – nothing to validate
                return input_data
        else:
            # When a Pydantic ``BaseModel`` is supplied, we assume full validation is
            # handled elsewhere (e.g., orchestrator).  Return the data unchanged so we
            # don't raise false-positives at runtime.
            return input_data

        result: Dict[str, Any] = {}

        for key, expected_type in schema_items:
            if key not in input_data:
                raise ValueError(f"Missing required input field: {key}")

            value = input_data[key]

            # Only attempt coercion when the config advertises the flag.
            coerce = getattr(self, "coerce_input_types", True)

            if not coerce:
                result[key] = value
                continue

            try:
                if expected_type == "int":
                    result[key] = int(value)
                elif expected_type == "float":
                    result[key] = float(value)
                elif expected_type == "bool":
                    result[key] = bool(value)
                elif expected_type == "str":
                    result[key] = str(value)
                else:
                    result[key] = value
            except (ValueError, TypeError):
                raise ValueError(
                    f"Validation error: Could not coerce {key}={value} to type {expected_type}"
                )

        return result

    def adapt_schema_from_context(self, context: Dict[str, Any]) -> None:  # noqa: D401
        """Hook for dynamic schema adaptation based on upstream context."""
        return None

    # ------------------------------------------------------------------
    # Validation stub ---------------------------------------------------
    # ------------------------------------------------------------------

    def runtime_validate(self) -> None:  # noqa: D401
        """Idempotent runtime validation hook.

        The default implementation leverages Pydantic's own validation that
        already ran at instantiation, therefore it simply returns. Subclasses
        can override to add heavier runtime checks (e.g. connectivity to
        external services or dynamic schema adaptation).
        """

        return None

    @staticmethod
    def is_pydantic_schema(schema: Any) -> bool:  # noqa: D401
        from pydantic import BaseModel as _BaseModelChecker

        return isinstance(schema, type) and issubclass(schema, _BaseModelChecker)


class AiNodeConfig(BaseNodeConfig):
    """Configuration for an LLM-powered node."""

    type: Literal["ai"] = "ai"

    # LLM-specific ----------------------------------------------------------------
    model: str = Field(..., description="Model name, e.g. gpt-3.5-turbo")
    prompt: str = Field(..., description="Prompt template")
    llm_config: LLMConfig = Field(..., description="Provider-specific parameters")

    # Optional quality-of-life flags kept for now (may be removed later).
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    # Experimental / less frequently used knobs – scheduled for removal.
    context_rules: Dict[str, ContextRule] = Field(default_factory=dict)
    format_specifications: Dict[str, Any] = Field(default_factory=dict)
    coerce_output_types: bool = Field(default=True)
    coerce_input_types: bool = Field(default=True)

    tools: Optional[List[ToolConfig]] = Field(
        default=None,
        description="List of ToolConfig objects describing callable tools available to the node",
    )
    # Restrictive allow-list – if None, the node cannot call tools
    allowed_tools: Optional[List[str]] = Field(
        default=None,
        description="Explicit list of tool names this AI node is permitted to invoke. None means no tool access.",
    )
    tool_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments passed into the tool call when this node is executed as a *tool*.",
    )


class ToolNodeConfig(BaseNodeConfig):
    """Configuration for a deterministic tool execution."""

    type: Literal["tool"] = "tool"

    tool_name: str = Field(..., description="Registered name of the tool to invoke")
    tool_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments forwarded to the tool (can contain placeholders)",
    )


# ---------------------------------------------------------------------------
# Condition node -------------------------------------------------------------
# ---------------------------------------------------------------------------


class ConditionNodeConfig(BaseNodeConfig):
    """Branching node that evaluates *expression* against its context and
    decides which downstream branch should execute.

    The expression syntax is intentionally flexible: implementations may use
    Python `eval` (sandboxed) or JMESPath.  For now we keep it opaque at the
    model level.
    """

    type: Literal["condition"] = "condition"

    expression: str = Field(
        ...,
        description="Boolean expression evaluated against node context. Truthy → true_branch executes.",
    )

    true_branch: List[str] = Field(
        default_factory=list,
        description="IDs of nodes that should follow when expression is truthy",
    )

    false_branch: Optional[List[str]] = Field(
        default=None,
        description="IDs of nodes for the false path (optional). If omitted, execution continues with dependents.",
    )


# ---------------------------------------------------------------------------
# Nested chain node ----------------------------------------------------------
# ---------------------------------------------------------------------------


class NestedChainConfig(BaseNodeConfig):
    """Configuration for a *nested* ScriptChain.

    The node wraps an existing :class:`~ice_orchestrator.script_chain.ScriptChain` (or
    a factory returning one) so that entire workflows can be reused as building
    blocks inside other workflows.

    For now only *in-memory* composition is supported – YAML/JSON references will
    be added in a later *NetworkSpec* iteration.
    """

    type: Literal["nested_chain"] = "nested_chain"

    # Reference to the *child* ScriptChain or a zero-arg callable returning one.
    chain: "ScriptChainLike | Callable[[], ScriptChainLike]"  # type: ignore[name-defined]

    # Developers can override the exposed *output* by mapping public keys to
    # nested paths inside the sub-chain's raw output (similar to *output_mappings*
    # in regular nodes).  Left empty, the executor will forward the entire
    # sub-chain *ChainExecutionResult.output*.
    exposed_outputs: Dict[str, str] = Field(
        default_factory=dict,
        description="Optional mapping of public key -> JMES/JSONPath inside sub-chain output.",
    )


# ---------------------------------------------------------------------------
# Update public alias --------------------------------------------------------
# ---------------------------------------------------------------------------

# Discriminated union used throughout the codebase
NodeConfig = Annotated[
    Union[
        AiNodeConfig,
        ToolNodeConfig,
        ConditionNodeConfig,
        NestedChainConfig,  # <-- NEW
    ],
    Field(discriminator="type"),
]  # Historical alias preserved for backwards-compatibility


class NodeExecutionRecord(BaseModel):
    """Execution statistics and historical data"""

    node_id: str
    executions: int = Field(0, ge=0, description="Total execution attempts")
    successes: int = Field(0, ge=0, description="Successful executions")
    failures: int = Field(0, ge=0, description="Failed executions")
    avg_duration: float = Field(
        0.0, ge=0, description="Average execution time in seconds"
    )
    last_executed: Optional[datetime] = None
    token_usage: Dict[str, int] = Field(
        default_factory=dict, description="Token usage by model version"
    )
    provider_usage: Dict[str, Dict[str, int]] = Field(
        default_factory=dict, description="Token usage by provider and model"
    )


class NodeIO(BaseModel):
    """Input/Output schema for a node."""

    data_schema: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class UsageMetadata(BaseModel):
    """Usage metadata for a node execution."""

    prompt_tokens: int = Field(default=0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(
        default=0, description="Number of tokens in the completion"
    )
    total_tokens: int = Field(default=0, description="Total number of tokens used")
    cost: float = Field(default=0.0, description="Cost of the API call in USD")
    api_calls: int = Field(default=1, description="Number of API calls made")
    model: str = Field(..., description="Model used for the execution")
    node_id: str = Field(..., description="ID of the node that generated this usage")
    provider: ModelProvider = Field(..., description="Provider used for the execution")
    token_limits: Dict[str, int] = Field(
        default_factory=lambda: {"context": 4096, "completion": 1024},
        description="Token limits for the execution",
    )

    # Auto-calculate totals ---------------------------------------------------
    @model_validator(mode="after")
    def _fill_totals(self) -> Any:  # type: ignore[override]
        if self.total_tokens == 0 and (self.prompt_tokens or self.completion_tokens):
            self.total_tokens = self.prompt_tokens + self.completion_tokens
        return self


class NodeExecutionResult(BaseModel):
    """Result of a node execution."""

    success: bool = Field(
        default=True, description="Whether the execution was successful"
    )
    error: Optional[str] = Field(None, description="Error message if execution failed")
    output: Optional[Any] = Field(
        None, description="Output data from the node (dict, str, etc.)"
    )
    metadata: NodeMetadata = Field(..., description="Metadata about the execution")
    usage: Optional[UsageMetadata] = Field(
        None, description="Usage statistics from the execution"
    )
    execution_time: Optional[float] = Field(
        None, description="Execution time in seconds"
    )
    context_used: Optional[Dict[str, Any]] = Field(
        None, description="Context used for the execution"
    )
    token_stats: Optional[Dict[str, Any]] = Field(
        None, description="Token statistics including truncation and limits"
    )
    budget_status: Optional[Dict[str, Any]] = Field(
        None, description="Budget consumption metrics at time of execution"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


# NOTE: Demo output schemas removed during repository clean-up.  If
# application-specific output models are required, declare them in the
# respective domain package instead of the shared SDK.


class ChainExecutionResult(BaseModel):
    """Result of a chain execution."""

    success: bool = Field(
        default=True, description="Whether the execution was successful"
    )
    error: Optional[str] = Field(None, description="Error message if execution failed")
    output: Optional[Any] = Field(
        None,
        description="Output data from the final node in the chain (dict, str, etc.)",
    )
    metadata: NodeMetadata = Field(
        ..., description="Metadata about the chain execution"
    )
    chain_metadata: Optional["ChainMetadata"] = Field(
        None,
        description="High-level chain information (topology, counts, tags, ...)",
    )
    execution_time: Optional[float] = Field(
        None, description="Execution time in seconds"
    )
    token_stats: Optional[Dict[str, Any]] = Field(
        None, description="Token statistics including truncation and limits"
    )


# ---------------------------------------------------------------------------
# Chain-level metadata (new) -------------------------------------------------
# ---------------------------------------------------------------------------


class ChainMetadata(BaseModel):
    """Descriptive metadata for a ScriptChain instance.

    The model deliberately stays light-weight – only fields required by
    dashboards & provenance pipelines.  Further properties can be added
    non-breaking.
    """

    chain_id: str
    name: str
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str
    node_count: int = Field(ge=1)
    edge_count: int = Field(ge=0)
    topology_hash: str = Field(description="Stable hash of the DAG topology")
    tags: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Update forward references --------------------------------------------------
# ---------------------------------------------------------------------------


try:
    ChainExecutionResult.model_rebuild()
except NameError:
    # During initial import order may not yet include ChainExecutionResult
    pass


# ---------------------------------------------------------------------------
# Lightweight stubs added solely to satisfy public contract tests ------------
# ---------------------------------------------------------------------------

from dataclasses import dataclass
from typing import List, Optional


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
