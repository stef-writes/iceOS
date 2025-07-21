"""NodeMetadata model extracted to core domain layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from .enums import ModelProvider

__all__: list[str] = [
    "NodeMetadata",
]


class NodeMetadata(BaseModel):
    """Metadata model for node versioning and ownership.

    This is a near verbatim copy of the former *ice_sdk.models.node_models.NodeMetadata*
    to kick-off the migration.  Once downstream code switches to this definition
    the legacy one will be deprecated and removed.
    """

    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(..., description="Type of node (ai)")
    name: Optional[str] = None
    version: str = Field(
        "1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version of node configuration",
    )
    owner: Optional[str] = Field(None, description="Node owner/maintainer")
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    description: Optional[str] = Field(None, description="Description of the node")
    error_type: Optional[str] = Field(
        None, description="Type of error if execution failed"
    )
    timestamp: Optional[datetime] = None
    start_time: Optional[datetime] = Field(None, description="Execution start time")
    end_time: Optional[datetime] = Field(None, description="Execution end time")
    duration: Optional[float] = Field(None, description="Execution duration in seconds")
    tags: List[str] = Field(
        default_factory=list,
        description="Categorisation tags for the node (e.g. 'safety', 'experimental')",
    )
    provider: Optional[ModelProvider] = Field(
        None, description="LLM provider used for execution"
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retry attempts performed during node execution",
    )

    # ------------------------------------------------------------------
    # Automatic timestamps & duration ----------------------------------
    # ------------------------------------------------------------------

    @model_validator(mode="before")  # type: ignore[override]
    @classmethod
    def _set_modified_at(cls, values: Dict[str, Any]) -> Dict[str, Any]:  # – validator
        values["modified_at"] = datetime.utcnow()
        return values

    @model_validator(mode="after")  # type: ignore[override]
    def _set_duration(self) -> "NodeMetadata":  # – validator
        if self.start_time and self.end_time and self.duration is None:
            self.duration = (self.end_time - self.start_time).total_seconds()
        elif self.start_time and self.duration is not None and self.end_time is None:
            from datetime import timedelta

            self.end_time = self.start_time + timedelta(seconds=self.duration)
        return self

    # ------------------------------------------------------------------
    # Ensure description & tags ----------------------------------------
    # ------------------------------------------------------------------

    @model_validator(mode="after")  # type: ignore[override]
    def _ensure_description_tags(self) -> "NodeMetadata":  # – validator
        if not self.description or not self.description.strip():
            self.description = f"Node {self.node_id} (type={self.node_type})"
        if not self.tags:
            self.tags = ["default"]
        return self
