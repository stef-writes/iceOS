"""Workflow protocol and SubDAG models for cross-layer communication."""

import hashlib
import json
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

NodeConfig = Any  # Alias for cross-layer type without import


@runtime_checkable
class WorkflowProto(Protocol):
    """Cross-layer interface for dynamic workflow construction.

    Example:
        class MyWorkflow:
            def add_node(self, config: NodeConfig) -> str: ...

        assert isinstance(MyWorkflow(), WorkflowProto)
    """

    def add_node(self, config: NodeConfig, depends_on: list[str] | None = None) -> str:
        """Adds a node to the workflow with optional dependencies.

        Args:
            config: Node configuration
            depends_on: List of node IDs this node depends on

        Returns:
            Assigned node ID
        """
        ...

    def to_dict(self) -> dict:
        """Serializes workflow to dict format for cross-layer transfer."""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowProto":
        """Deserializes workflow from dict format."""
        ...

    def validate(self) -> None:
        """Performs integrity checks on the workflow.

        Raises:
            SubDAGError: If validation fails
        """
        ...


class SubDAGResult(BaseModel):
    """Container for agent-generated subworkflows.

    Example:
        SubDAGResult(
            workflow_data={"nodes": [...]},
            idempotency_key=sha256_hash
        )
    """

    workflow_data: dict = Field(
        ..., description="Serialized workflow data using WorkflowProto.to_dict()"
    )
    idempotency_key: str = Field(
        ...,
        description="SHA-256 hash of workflow_data for duplicate detection",
        min_length=64,
        max_length=64,
    )

    @classmethod
    def from_workflow(cls, workflow: WorkflowProto) -> "SubDAGResult":
        """Helper to create from a WorkflowProto instance."""
        data = workflow.to_dict()
        return cls(
            workflow_data=data,
            idempotency_key=hashlib.sha256(
                json.dumps(data, sort_keys=True).encode()
            ).hexdigest(),
        )
