"""Plugins manifest models (plugins.v0).

See docs/Design/MANIFEST_DRIVEN_REGISTRY.md for full spec.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Nested structures ---------------------------------------------------------
# ---------------------------------------------------------------------------

class CostEstimate(BaseModel):
    """Simple cost estimate used for marketplace previews."""

    base: float = Field(ge=0.0)
    per_token: float = Field(0.0, ge=0.0)


class DeprecatedInfo(BaseModel):
    since: str = Field(..., description="Semantic version when deprecation started")
    replacement: Optional[str] = Field(None, description="Suggested replacement component")


class SignatureInfo(BaseModel):
    algo: Literal["ed25519"] = "ed25519"  # Only algo supported for now
    value: str = Field(..., description="Base64-encoded detached signature")
    public_key_id: str = Field(..., description="Key identifier for verification")


# ---------------------------------------------------------------------------
# Component & Manifest ------------------------------------------------------
# ---------------------------------------------------------------------------

class ComponentEntry(BaseModel):
    node_type: Literal["tool", "agent", "workflow"] = Field(..., alias="node_type")
    name: str = Field(..., min_length=1, regex=r"^[a-zA-Z0-9_]+$")
    import_path: str = Field(..., alias="import", description="module:attribute import path")
    version: str = Field("1.0.0", regex=r"^\d+\.\d+\.\d+$")
    iceos_min: Optional[str] = Field(None, description="Minimum compatible iceOS version")
    schema: Optional[Dict[str, Any]] = None  # Input/output schema refs
    cost_estimate: Optional[CostEstimate] = None
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    deprecated: Optional[DeprecatedInfo] = None

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


class PluginsManifest(BaseModel):
    """Manifest root (schema_version MUST be plugins.v0)."""

    schema_version: Literal["plugins.v0"] = "plugins.v0"
    created: _dt.datetime = Field(default_factory=_dt.datetime.utcnow)
    components: List[ComponentEntry] = Field(min_items=1)
    signature: Optional[SignatureInfo] = None

    @model_validator(mode="after")
    def _unique_component_names(self) -> "PluginsManifest":
        names = [c.name for c in self.components]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate component names in manifest")
        return self


__all__ = [
    "CostEstimate",
    "DeprecatedInfo",
    "SignatureInfo",
    "ComponentEntry",
    "PluginsManifest",
] 