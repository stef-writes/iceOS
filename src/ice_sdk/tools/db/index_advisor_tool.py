"""Re-export stub index_advisor_tool for contract tests."""

from __future__ import annotations

from ice_sdk.tools.base import ToolContext, function_tool


@function_tool()
async def index_advisor_tool(
    ctx: ToolContext, table: str, query_samples: list[str]
) -> dict[str, list[str]]:  # noqa: D401 – stub
    """Return naive column suggestion based on simple WHERE clauses."""

    suggestions: list[str] = []
    for q in query_samples:
        if "where" in q.lower():
            parts = q.lower().split("where")[-1].strip().split()
            if parts:
                suggestions.append(parts[0])

    return {"suggestions": suggestions or ["id"]}


__all__ = ["index_advisor_tool"]
