from __future__ import annotations

from typing import Any, ClassVar, Dict

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["ExplainPlanSkill"]


class ExplainPlanSkill(SkillBase):
    """Explain the execution plan for a SQL query."""

    name: str = "explain_plan"
    description: str = "Explain the execution plan for a SQL query"
    tags: ClassVar[list[str]] = ["db", "explain", "utility"]

    def get_required_config(self) -> list[str]:
        return []

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        sql = kwargs.get("sql")
        if not isinstance(sql, str):
            raise SkillExecutionError("'sql' must be a string")

        # Simple fake plan splitting tokens
        steps = [token for token in sql.strip().split() if token]
        return {"plan": [{"step": idx, "op": tok} for idx, tok in enumerate(steps)]}
