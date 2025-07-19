from __future__ import annotations

from typing import Any, Dict, List

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["SumSkill"]


class SumSkill(SkillBase):
    """Return the arithmetic sum of a list of numbers."""

    name: str = "sum"
    description: str = "Add a list of numbers and return the total"
    tags: List[str] = ["math", "utility"]

    def get_required_config(self) -> list[str]:  # noqa: D401
        return []

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        numbers_raw = kwargs.get("numbers")
        if not isinstance(numbers_raw, list):
            raise SkillExecutionError("'numbers' must be list[float]")
        try:
            numbers: List[float] = [float(n) for n in numbers_raw]
        except Exception as exc:
            raise SkillExecutionError("'numbers' must contain numeric values") from exc
        return {"sum": sum(numbers)}
