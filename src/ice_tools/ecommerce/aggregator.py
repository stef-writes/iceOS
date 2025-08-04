"""AggregatorTool – summarise per-item listing results.

Takes a list of per-item outputs (dictionaries) and returns totals for UI /
metrics.  Pure function – no external I/O.
"""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import Field

from ice_core.base_tool import ToolBase
from ice_core.exceptions import ValidationError
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry

__all__: list[str] = ["AggregatorTool"]


class AggregatorTool(ToolBase):
    """Aggregate list of listing results into a single summary object."""

    # Metadata --------------------------------------------------------------

    # Pre-declare output schema for discovery
    output_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "total": {"type": "integer"},
            "success": {"type": "integer"},
            "failures": {"type": "integer"},
            "items": {
                "type": "array",
                "items": {"type": "object"},
            },
        },
        "required": ["total", "success", "failures", "items"],
        "additionalProperties": False,
    }
    name: str = "aggregator"
    description: str = "Aggregate list of listing results into summary totals."

    # Config ----------------------------------------------------------------
    max_items: int = Field(1000, ge=1, description="Safety cap on result list size")

    # Execution -------------------------------------------------------------
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = kwargs.get("results", [])
        if len(results) > self.max_items:
            raise ValidationError("Too many items to aggregate – increase max_items if intentional")

        success = [r for r in results if r.get("listing_id")]
        failures = [r for r in results if r.get("error")]
        return {
            "total": len(results),
            "success": len(success),
            "failures": len(failures),
            "items": results,
        }

    # ------------------------------------------------------------------
    # Schema overrides --------------------------------------------------
    # ------------------------------------------------------------------

    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:  # noqa: D401 – override
        """JSON Schema for aggregated listing results."""
        return {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "success": {"type": "integer"},
                "failures": {"type": "integer"},
                "items": {
                    "type": "array",
                    "items": {"type": "object", "additionalProperties": True},
                },
            },
            "required": ["total", "success", "failures", "items"],
            "additionalProperties": False,
        }


# Auto-registration ---------------------------------------------------------
_instance = AggregatorTool()
registry.register_instance(NodeType.TOOL, _instance.name, _instance, validate=False)  # type: ignore[arg-type]
