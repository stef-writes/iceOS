from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from ice_core.base_tool import ToolBase
from ice_core.unified_registry import registry


class AggregatorConcatTool(ToolBase):
    name: str = "aggregator_concat"
    description: str = Field(
        "Concatenate upstream outputs into a single string or JSON array.",
    )

    async def _execute_impl(
        self,
        *,
        inputs: Optional[List[Any]] = None,
        key: Optional[str] = None,
        sep: str = "\n",
        as_json_array: bool = False,
    ) -> Dict[str, Any]:
        values: List[Any] = []
        if isinstance(inputs, list):
            values.extend(inputs)
        # If a specific key is provided, try extract that key from dict-like inputs
        if key:
            extracted: List[Any] = []
            for v in values:
                if isinstance(v, dict) and key in v:
                    extracted.append(v[key])
                else:
                    extracted.append(v)
            values = extracted
        if as_json_array:
            return {"items": values}
        # Fallback: stringify and join
        return {"text": sep.join(str(v) for v in values)}


def create_aggregator_concat_tool(**kwargs: Any) -> AggregatorConcatTool:
    return AggregatorConcatTool(**kwargs)


registry.register_tool_factory(
    "aggregator_concat", __name__ + ":create_aggregator_concat_tool"
)
