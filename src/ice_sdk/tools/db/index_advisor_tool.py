from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ...utils.errors import ToolExecutionError
from ..base import ToolBase
from ..base import ToolBase

__all__ = ["IndexAdvisorTool"]

class IndexAdvisorTool(ToolBase):
    """Provide index recommendations for SQL queries."""

    name: str = "index_advisor"
    description: str = "Provide index recommendations for SQL queries"
    tags: ClassVar[list[str]] = ["db", "index", "advisor"]

    def get_required_config(self) -> list[str]:
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
            raise ToolExecutionError("'table' must be a string")
        if not isinstance(queries, list):
            raise ToolExecutionError("'query_samples' must be list[str]")

        suggestions: List[str] = []
        for q in queries:
            if "where" in q.lower():
                parts = q.lower().split("where")[-1].strip().split()
                if parts:
                    suggestions.append(parts[0])

        return {"suggestions": suggestions or ["id"]}
