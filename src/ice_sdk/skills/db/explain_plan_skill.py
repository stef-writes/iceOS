from __future__ import annotations

from typing import Any, Dict

from ..base import SkillBase
from ...utils.errors import SkillExecutionError

__all__ = ["ExplainPlanSkill"]


class ExplainPlanSkill(SkillBase):
    """Return a fake EXPLAIN plan for demonstration purposes."""

    name: str = "explain_plan"
    description: str = "Generate a naive SQL EXPLAIN plan (stub)."
    tags = ["db", "explain", "utility"]

    def get_required_config(self):
        return []

    async def _execute_impl(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        sql = input_data.get("sql")
        if not isinstance(sql, str):
            raise SkillExecutionError("'sql' must be a string")

        # Simple fake plan splitting tokens
        steps = [token for token in sql.strip().split() if token]
        return {"plan": [{"step": idx, "op": tok} for idx, tok in enumerate(steps)]} 