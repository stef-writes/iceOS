"""MCP (Model Context Protocol) models for cross-layer communication.

These models define the contract between design tools (like Frosty) and
the runtime execution engine. They are shared across all layers to ensure
consistency.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Dict, List, Optional, Union, Literal

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Blueprint & nodes ----------------------------------------------------------
# ---------------------------------------------------------------------------

class NodeSpec(BaseModel):
    """JSON-friendly node description (same keys as NodeConfig)."""

    id: str
    type: str
    dependencies: List[str] = Field(default_factory=list)

    # Accept arbitrary extra fields so callers can embed the full NodeConfig.
    model_config = {"extra": "allow"}

# ---------------------------------------------------------------------------
# Blueprint model -----------------------------------------------------------
# ---------------------------------------------------------------------------

class Blueprint(BaseModel):
    """A design-time workflow blueprint transferable over the wire."""

    blueprint_id: str = Field(default_factory=lambda: f"bp_{uuid.uuid4().hex[:8]}")
    schema_version: str = Field(
        "1.1.0",
        description="Semver blueprint schema version",
        json_schema_extra={"example": "1.1.0"}
    )
    nodes: List[NodeSpec] = Field(
        ...,  # At least one node required (runtime validator asserts)
        description="Nodes comprising the workflow"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata for documentation"
    )

    @model_validator(mode='after')
    def validate_dependencies(cls, values: Any) -> Any:
        """Ensure no circular dependencies and valid node references"""
        node_ids = {n.id for n in values.nodes}
        for node in values.nodes:
            for dep in node.dependencies:
                if dep not in node_ids:
                    raise ValueError(f"Node {node.id} references missing dependency {dep}")
        return values

    # ------------------------------------------------------------------
    # Validation helpers -------------------------------------------------
    # ------------------------------------------------------------------

    def validate_runtime(self) -> None:
        """Fail fast if any contained NodeSpec cannot be converted.

        This helper is *side-effect free*; it merely attempts a conversion
        using the central registry so that invalid blueprints are rejected
        early – either at registration time or before inline execution.
        """

        from ice_core.utils.node_conversion import convert_node_specs

        # Will raise ValueError / ValidationError on failure
        convert_node_specs(self.nodes)

class BlueprintAck(BaseModel):
    """Acknowledgement for blueprint registration."""

    blueprint_id: str
    status: str = "accepted"  # accepted | updated

# ---------------------------------------------------------------------------
# Partial Blueprint Support for Incremental Construction ---------------------
# ---------------------------------------------------------------------------

class PartialNodeSpec(NodeSpec):
    """Node spec that allows pending connections."""
    
    pending_inputs: Optional[List[str]] = Field(
        default=None,
        description="Input fields awaiting connection"
    )
    pending_outputs: Optional[List[str]] = Field(
        default=None,
        description="Output fields that could connect to other nodes"
    )
    suggestions: Optional[List[str]] = Field(
        default=None,
        description="Suggested next node types"
    )

class PartialBlueprint(BaseModel):
    """Blueprint under construction with validation relaxed."""
    
    blueprint_id: str = Field(default_factory=lambda: f"partial_bp_{uuid.uuid4().hex[:8]}")
    schema_version: str = Field("1.1.0")
    nodes: List[Union[NodeSpec, PartialNodeSpec]] = Field(
        default_factory=list,
        description="Nodes added so far (can be empty)"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Incremental construction state
    is_complete: bool = Field(
        default=False,
        description="Whether blueprint is ready for execution"
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="Current validation issues"
    )
    next_suggestions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="AI suggestions for next nodes"
    )
    
    def add_node(self, node: Union[NodeSpec, PartialNodeSpec]) -> None:
        """Add a node and revalidate incrementally."""
        self.nodes.append(node)
        self._validate_incremental()
    
    def _validate_incremental(self) -> None:
        """Validate what we have so far, populate errors/suggestions."""
        self.validation_errors.clear()
        self.next_suggestions.clear()
        
        # Check for unconnected dependencies
        node_ids = {n.id for n in self.nodes}
        for node in self.nodes:
            for dep in node.dependencies:
                if dep not in node_ids:
                    self.validation_errors.append(
                        f"Node {node.id} references missing dependency {dep}"
                    )
        
        # Check for pending connections
        has_pending = any(
            isinstance(n, PartialNodeSpec) and (n.pending_inputs or n.pending_outputs)
            for n in self.nodes
        )
        
        # Mark complete if no errors and no pending connections
        self.is_complete = len(self.validation_errors) == 0 and not has_pending
        
        # Generate suggestions based on current state
        if self.nodes:
            last_node = self.nodes[-1]
            if last_node.type == "tool" and hasattr(last_node, "output_schema"):
                self.next_suggestions.append({
                    "type": "llm",
                    "reason": "Process tool output with LLM",
                    "suggested_connection": last_node.id
                })
            elif last_node.type == "llm":
                self.next_suggestions.append({
                    "type": "tool", 
                    "reason": "Execute action based on LLM output",
                    "suggested_connection": last_node.id
                })
    
    def to_blueprint(self) -> Blueprint:
        """Convert to executable blueprint (raises if not complete)."""
        if not self.is_complete:
            raise ValueError(
                f"Cannot convert incomplete blueprint. Errors: {self.validation_errors}"
            )
        
        # Convert all PartialNodeSpec to NodeSpec
        nodes = []
        for node in self.nodes:
            if isinstance(node, PartialNodeSpec):
                nodes.append(NodeSpec(
                    id=node.id,
                    type=node.type,
                    dependencies=node.dependencies,
                    **{k: v for k, v in node.model_extra.items()}
                ))
            else:
                nodes.append(node)
        
        return Blueprint(
            blueprint_id=self.blueprint_id.replace("partial_", ""),
            nodes=nodes,
            metadata=self.metadata
        )

class PartialBlueprintUpdate(BaseModel):
    """Request to update a partial blueprint."""
    
    action: Literal["add_node", "remove_node", "update_node", "suggest"]
    node: Optional[Union[NodeSpec, PartialNodeSpec]] = None
    node_id: Optional[str] = None
    updates: Optional[Dict[str, Any]] = None

# ---------------------------------------------------------------------------
# Run helpers ----------------------------------------------------------------
# ---------------------------------------------------------------------------

class RunOptions(BaseModel):
    """Options for workflow execution."""

    max_parallel: int = Field(5, ge=1, le=20)

class RunRequest(BaseModel):
    """Request to execute a workflow."""

    blueprint_id: Optional[str] = None
    blueprint: Optional[Blueprint] = None
    options: RunOptions = Field(default_factory=lambda: RunOptions(max_parallel=5))

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _at_least_one(self) -> "RunRequest":  # – pydantic hook
        """Ensure one of *blueprint* or *blueprint_id* is supplied."""

        if self.blueprint is None and self.blueprint_id is None:
            raise ValueError("Either blueprint or blueprint_id must be provided")

        return self

class RunAck(BaseModel):
    """Acknowledgement for run start."""

    run_id: str
    status_endpoint: str
    events_endpoint: str

class RunResult(BaseModel):
    """Result of workflow execution."""

    run_id: str
    success: bool
    start_time: _dt.datetime
    end_time: _dt.datetime
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

# ---------------------------------------------------------------------------
# Utilities ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def uuid4_hex() -> str:  # – helper
    """Generate a UUID4 hex string."""
    return uuid.uuid4().hex
