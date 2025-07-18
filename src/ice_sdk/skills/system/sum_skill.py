from __future__ import annotations

from typing import Any, List, Dict

from ..base import SkillBase
from ...utils.errors import SkillExecutionError

__all__ = ["SumSkill"]


class SumSkill(SkillBase):
    """Return the arithmetic sum of a list of numbers."""

    name: str = "sum"
    description: str = "Add a list of numbers and return the total"
    tags: List[str] = ["math", "utility"]

    def get_required_config(self):  # noqa: D401
        return []

    async def _execute_impl(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        numbers_raw = input_data.get("numbers", [])
        if not isinstance(numbers_raw, list):
            raise SkillExecutionError("'numbers' must be an array of numbers")

        numbers: List[float] = []
        try:
            for x in numbers_raw:
                numbers.append(float(x))
        except Exception as exc:  # noqa: BLE001
            raise SkillExecutionError(f"Invalid number in input: {exc}") from exc

        return {"sum": sum(numbers)} 