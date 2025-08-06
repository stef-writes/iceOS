"""MCP (Model Context Protocol) models for cross-layer communication.

These models define the contract between design tools (like Frosty) and
the runtime execution engine. They are shared across all layers to ensure
consistency.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Dict, List, Literal, Optional, Union, cast

from pydantic import BaseModel, Field, model_validator, field_validator

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
        "1.2.0",
        description="Semver blueprint schema version",
        json_schema_extra={"example": "1.2.0"}
    )
    nodes: List[NodeSpec] = Field(
        ...,  # At least one node required (runtime validator asserts)
        description="Nodes comprising the workflow"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata for documentation"
    )

    @property
    def name(self) -> str:
        """Return user-facing name for blueprint (draft_name metadata fallback)."""
        return str(self.metadata.get("draft_name", self.blueprint_id))

    @field_validator("nodes", mode="after")
    def _validate_node_dependencies(cls, nodes: List[NodeSpec]) -> List[NodeSpec]:
        """Ensure no circular dependencies and valid node references."""
        node_ids = {n.id for n in nodes}
        for node in nodes:
            for dep in node.dependencies:
                if dep not in node_ids:
                    raise ValueError(
                        f"Node {node.id} references missing dependency {dep}"
                    )
        return nodes

    # ------------------------------------------------------------------
    # Validation helpers -------------------------------------------------
    # ------------------------------------------------------------------

    def validate_runtime(self) -> None:
        """Fail fast if any contained NodeSpec cannot be converted.

        This helper is *side-effect free*; it merely attempts a conversion
        using the central registry so that invalid blueprints are rejected
        early – either at registration time or before inline execution.
        """
        # Import here to avoid circular dependency
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
    next_suggestions: List[str] = Field(
        default_factory=list,
        description="AI suggestions for next nodes"
    )
    
    def add_node(self, node: Union[NodeSpec, PartialNodeSpec]) -> None:
        """Add a node and revalidate incrementally."""
        self.nodes.append(node)
        self._validate_incremental()
    
    def _validate_incremental(self) -> None:
        """Incrementally validate the partial blueprint."""
        self.validation_errors = []
        self.is_complete = False
        
        if not self.nodes:
            self.validation_errors.append("No nodes added yet")
            return
            
        # Check each node's dependencies
        node_ids = {node.id for node in self.nodes}
        for node in self.nodes:
            for dep in node.dependencies:
                if dep not in node_ids:
                    self.validation_errors.append(
                        f"Node {node.id} depends on non-existent node {dep}"
                    )
        
        # Check for unresolved inputs/outputs
        for node in self.nodes:
            if isinstance(node, PartialNodeSpec):
                if node.pending_inputs:
                    self.validation_errors.append(
                        f"Node {node.id} has unconnected inputs: {node.pending_inputs}"
                    )
        
        # Check if referenced components exist
        from ice_core.models import NodeType
        from ice_core.unified_registry import global_agent_registry, registry
        
        for node in self.nodes:
            if node.type == "tool" and hasattr(node, 'tool_name'):
                if not registry.has_tool(node.tool_name):
                    self.validation_errors.append(
                        f"Tool '{node.tool_name}' not found in registry"
                    )
                    self.next_suggestions.append(
                        f"Use /components/validate to validate and register tool '{node.tool_name}'"
                    )
            elif node.type == "agent" and hasattr(node, 'package'):
                agent_names = [name for name, _ in global_agent_registry.available_agents()]
                if node.package not in agent_names:
                    self.validation_errors.append(
                        f"Agent '{node.package}' not found in registry"
                    )
                    self.next_suggestions.append(
                        f"Use /components/validate to validate and register agent '{node.package}'"
                    )
            elif node.type == "workflow" and hasattr(node, 'workflow_ref'):
                try:
                    registry.get_instance(NodeType.WORKFLOW, node.workflow_ref)
                except Exception:
                    self.validation_errors.append(
                        f"Workflow '{node.workflow_ref}' not found in registry"
                    )
                    self.next_suggestions.append(
                        f"Use /components/validate to validate and register workflow '{node.workflow_ref}'"
                    )
        
        # Generate suggestions based on current state
        if not self.validation_errors:
            self.is_complete = len(self.nodes) > 0
            if self.is_complete:
                self.next_suggestions.append("Blueprint is valid! Use to_blueprint() to finalize")
            else:
                self.next_suggestions.append("Add nodes to start building your workflow")
    
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
                    **{k: v for k, v in node.model_extra.items()} if node.model_extra else {}
                ))
            else:
                nodes.append(node)
        
        return Blueprint(
            blueprint_id=self.blueprint_id.replace("partial_", ""),
            schema_version="1.1.0",
            nodes=nodes,
            metadata=self.metadata
        )

class PartialBlueprintUpdate(BaseModel):
    """Update operation for partial blueprints."""
    
    action: Literal["add_node", "remove_node", "update_node", "suggest"]
    node: Optional[PartialNodeSpec] = None
    node_id: Optional[str] = None
    updates: Optional[Dict[str, Any]] = None

# ---------------------------------------------------------------------------
# Component Definition and Validation Support --------------------------------
# ---------------------------------------------------------------------------

class ComponentDefinition(BaseModel):
    """Definition for a new component to validate and potentially register.
    
    This enables validating tool/agent/workflow definitions BEFORE registration,
    ensuring only valid components enter the registry.
    """
    type: Literal["tool", "agent", "workflow"]
    name: str = Field(..., description="Unique component name")
    description: str = Field(..., description="Component description")
    
    # For tools - Python code or config
    tool_factory_code: Optional[str] = Field(
        None,
        description="Python code defining a *factory function* that returns ToolBase"
    )
    tool_class_code: Optional[str] = Field(
        None, 
        description="Python code defining the tool class (must inherit from ToolBase)"
    )
    tool_input_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON schema for tool inputs"
    )
    tool_output_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON schema for tool outputs"
    )
    
    # For agents
    agent_system_prompt: Optional[str] = Field(None, description="Agent system prompt")
    agent_tools: Optional[List[str]] = Field(
        None,
        description="List of tool names this agent can use"
    )
    agent_llm_config: Optional[Dict[str, Any]] = Field(
        None,
        description="LLM configuration for the agent"
    )
    
    # For workflows
    workflow_nodes: Optional[List[NodeSpec]] = Field(
        None,
        description="Nodes that make up the workflow"
    )
    
    # Registration options
    auto_register: bool = Field(
        True,
        description="Automatically register if validation passes"
    )
    validate_only: bool = Field(
        False,
        description="Only validate, never register (overrides auto_register)"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "ComponentDefinition":
        """Ensure type-specific fields are provided."""
        if self.type == "tool":
            if not (self.tool_factory_code or self.tool_class_code or self.tool_input_schema):
                raise ValueError("Tool definition requires either tool_class_code or schemas")
        elif self.type == "agent":
            if not self.agent_system_prompt and not self.agent_tools:
                raise ValueError("Agent definition requires system_prompt or tools")
        elif self.type == "workflow":
            if not self.workflow_nodes:
                raise ValueError("Workflow definition requires nodes")
        return self


class ComponentValidationResult(BaseModel):
    """Result of component definition validation."""
    
    valid: bool = Field(..., description="Whether the component is valid")
    errors: List[str] = Field(
        default_factory=list,
        description="Validation errors that must be fixed"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings that should be addressed"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="AI suggestions for improvement"
    )
    
    # Registration status
    registered: bool = Field(
        False,
        description="Whether the component was registered"
    )
    registry_name: Optional[str] = Field(
        None,
        description="Name used in registry (may differ from definition.name)"
    )
    
    # Component metadata
    component_type: Optional[str] = None
    component_id: Optional[str] = Field(
        None,
        description="Unique ID assigned to the component"
    )
    
    # For debugging
    validation_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed validation information"
    )

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
