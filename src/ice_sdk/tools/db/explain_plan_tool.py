from __future__ import annotations

from typing import Any, ClassVar, Dict

from ...utils.errors import ToolExecutionError
from ..base import ToolBase
from ..base import ToolBase

__all__ = ["ExplainPlanTool"]

class ExplainPlanTool(ToolBase):
    """Explain the execution plan for a SQL query."""

    name: str = "explain_plan"
    description: str = "Explain the execution plan for a SQL query"
    tags: ClassVar[list[str]] = ["db", "explain", "utility"]

    def get_required_config(self) -> list[str]:
        return []

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        sql = kwargs.get("sql")
        if not isinstance(sql, str):
            raise ToolExecutionError("explain_plan", "'sql' must be a string")

        # Simple fake plan splitting tokens
        steps = [token for token in sql.strip().split() if token]
        return {"plan": [{"step": idx, "op": tok} for idx, tok in enumerate(steps)]}
