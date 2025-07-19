from __future__ import annotations

from typing import Any, Dict, List

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["IndexAdvisorSkill"]


class IndexAdvisorSkill(SkillBase):
    """Suggest naive index columns based on WHERE clauses."""

    name: str = "index_advisor"
    description: str = "Suggest index columns based on sample queries."
    tags = ["db", "index", "advisor"]

    def get_required_config(self):
        return []

    async def _execute_impl(
        self,
        *,
        table: str | None = None,
        query_samples: List[str] | None = None,
        input_data: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if input_data is not None:
            table = table or input_data.get("table")  # type: ignore[assignment]
            query_samples = query_samples or input_data.get("query_samples", [])

        queries = query_samples or []
        if not isinstance(table, str):
            raise SkillExecutionError("'table' must be a string")
        if not isinstance(queries, list):
            raise SkillExecutionError("'query_samples' must be list[str]")

        suggestions: List[str] = []
        for q in queries:
            if "where" in q.lower():
                parts = q.lower().split("where")[-1].strip().split()
                if parts:
                    suggestions.append(parts[0])

        return {"suggestions": suggestions or ["id"]}
