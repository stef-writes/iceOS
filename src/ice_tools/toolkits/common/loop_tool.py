from __future__ import annotations

"""LoopTool – second-class looping utility.

Executes an inner tool for every element in *items* and returns the list of
outputs.  Keeps looping semantics inside one node so it plays nicely with the
"each node runs once" contract of the orchestrator.
"""

from typing import Any, Dict, List

from pydantic import Field, PositiveInt

from ice_core.base_tool import ToolBase
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType
from ice_core.exceptions import ValidationError

__all__: list[str] = ["LoopTool"]


class LoopTool(ToolBase):
    """Iterate over *items* and run *tool* for each element."""

    name: str = "loop_tool"
    description: str = "Run another tool for every element in a list and aggregate results"

    # Config ------------------------------------------------------------------
    tool: str = Field(..., description="Registry name of the inner tool to execute")
    item_var: str = Field("item", description="Parameter name for the current item")
    max_items: PositiveInt = Field(1000, description="Safety cap to avoid huge loops")

    # Schema ------------------------------------------------------------------
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:  # noqa: D401 – override
        return {
            "type": "object",
            "properties": {
                "items": {"type": "array"},
            },
            "required": ["items"],
            "additionalProperties": True,
        }

    async def _execute_impl(self, **kwargs: Any) -> List[Any]:  # noqa: D401
        items = kwargs.get("items")
        if not isinstance(items, list):
            raise ValidationError("'items' must be a list")
        if len(items) > self.max_items:
            raise ValidationError("Too many items – increase max_items if intentional")

        # Get inner tool instance once (fresh instance per execution)
        inner_tool = registry.get_instance(NodeType.TOOL, self.tool)

        results: list[Any] = []
        for itm in items:
            ctx = {self.item_var: itm, **kwargs}
            ctx.pop("items", None)
            res = await inner_tool.execute(**ctx)
            results.append(res)
        return {"results": results}


# Auto-registration -----------------------------------------------------------
_instance = LoopTool(tool="listing_agent")  # default stub; config overridden at runtime
registry.register_instance(NodeType.TOOL, _instance.name, _instance, validate=False)  # type: ignore[arg-type]
