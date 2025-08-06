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
        """Execute with context-first approach - intelligently find results."""
        results = self._extract_results(kwargs)
        
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
    
    def _extract_results(self, context: Dict[str, Any]) -> list[dict[str, Any]]:
        """Extract results from various context structures."""
        
        # Direct results parameter
        if "results" in context and isinstance(context["results"], list):
            return context["results"]
        
        # Look for common loop output names
        for key in ["listing_loop", "process_loop", "process_items", "loop_results", "items"]:
            if key in context:
                value = context[key]
                if isinstance(value, list):
                    return value
                elif isinstance(value, dict) and "results" in value:
                    return value["results"]
        
        # Check if context values look like loop results
        for key, value in context.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                # Looks like a list of results
                if any(k in value[0] for k in ["listing_id", "title", "error"]):
                    return value
        
        # Default to empty list
        return []

    # ------------------------------------------------------------------
    # Schema overrides --------------------------------------------------
    # ------------------------------------------------------------------

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:  # noqa: D401 – override
        """Accept any input parameters - let DAG context management handle it."""
        return {
            "type": "object",
            "additionalProperties": True,  # Accept all context parameters
        }

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


# Factory function for creating AggregatorTool instances
def create_aggregator_tool(max_items: int = 1000) -> AggregatorTool:
    """Create an AggregatorTool with the specified configuration."""
    return AggregatorTool(max_items=max_items)

# Auto-registration ---------------------------------------------------------
from ice_core.unified_registry import register_tool_factory

register_tool_factory("aggregator", "ice_tools.toolkits.ecommerce.aggregator:create_aggregator_tool")
