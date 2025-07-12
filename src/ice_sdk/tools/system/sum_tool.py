"""Sum tool for mathematical operations."""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ..base import BaseTool, ToolError


class SumTool(BaseTool):
    """Return the arithmetic sum of a list of numbers."""

    name: ClassVar[str] = "sum"
    description: ClassVar[str] = "Add a list of numbers and return the total"
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "numbers": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Numbers to add",
            }
        },
        "required": ["numbers"],
    }
    tags: ClassVar[List[str]] = ["math", "utility"]

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "sum": {"type": "number", "description": "Total of input numbers"},
        },
        "required": ["sum"],
    }

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        numbers_raw = kwargs.get("numbers", [])
        if not isinstance(numbers_raw, list):
            raise ToolError("'numbers' must be an array of numbers")

        # Validate inner elements are numeric-like ---------------------------------
        numbers: List[float] = []
        try:
            for x in numbers_raw:
                numbers.append(float(x))
        except Exception as exc:  # noqa: BLE001 – propagate as ToolError
            raise ToolError(f"Invalid number in input: {exc}") from exc

        total: float = sum(numbers)
        return {"sum": total}
