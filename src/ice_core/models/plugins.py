"""Plugins manifest models (plugins.v0).

See docs/Design/MANIFEST_DRIVEN_REGISTRY.md for full spec.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Nested structures ---------------------------------------------------------
# ---------------------------------------------------------------------------

class CostEstimate(BaseModel):
    """Simple cost estimate used for marketplace previews."""

    base: float = Field(ge=0.0)
    per_token: float = Field(default=0.0, ge=0.0)


class DeprecatedInfo(BaseModel):
    since: str = Field(description="Semantic version when deprecation started")
    replacement: Optional[str] = Field(default=None, description="Suggested replacement component")


class SignatureInfo(BaseModel):
    algo: Literal["ed25519"] = Field(default="ed25519", description="Only algo supported for now")
    value: str = Field(description="Base64-encoded detached signature")
    public_key_id: str = Field(description="Key identifier for verification")


# ---------------------------------------------------------------------------
# Component & Manifest ------------------------------------------------------
# ---------------------------------------------------------------------------

class ComponentEntry(BaseModel):
    node_type: Literal["tool", "agent", "workflow"] = Field(alias="node_type")
    name: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_]+$")
    import_path: str = Field(alias="import", description="module:attribute import path")
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    iceos_min: Optional[str] = Field(default=None, description="Minimum compatible iceOS version")
    schema_data: Optional[Dict[str, Any]] = Field(default=None, alias="schema")  # Input/output schema refs
    cost_estimate: Optional[CostEstimate] = Field(default=None)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = Field(default=None)
    deprecated: Optional[DeprecatedInfo] = Field(default=None)

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )


class PluginsManifest(BaseModel):
    """Manifest root (schema_version MUST be plugins.v0)."""

    schema_version: Literal["plugins.v0"] = Field(default="plugins.v0")
    created: _dt.datetime = Field(default_factory=_dt.datetime.utcnow)
    components: List[ComponentEntry] = Field(description="List of component entries")
    signature: Optional[SignatureInfo] = Field(default=None)

    @model_validator(mode="after")
    def _unique_component_names(self) -> "PluginsManifest":
        names = [c.name for c in self.components]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate component names in manifest")
        if len(self.components) == 0:
            raise ValueError("At least one component is required")
        return self


__all__ = [
    "CostEstimate",
    "DeprecatedInfo",
    "SignatureInfo",
    "ComponentEntry",
    "PluginsManifest",
] 