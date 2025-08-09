"""Lookup tool – returns mock notes for a given query.

Production implementations should fetch from real data sources.
"""

from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from ice_core.base_tool import ToolBase
from ice_core.unified_registry import register_tool_factory


class LookupTool(ToolBase):
    """Return simple notes for a query.

    Parameters
    ----------
    source : str
        Optional data source label for observability.

    Example
    -------
    >>> tool = create_lookup_tool()
    >>> out = asyncio.run(tool.execute(query="renewable energy"))
    >>> assert "notes" in out
    """

    name: str = "lookup_tool"
    description: str = Field("Return concise notes for a query")
    source: str = Field("demo", description="Source label")

    async def _execute_impl(self, *, query: str) -> Dict[str, Any]:  # noqa: D401
        """Return notes for *query*.

        Parameters
        ----------
        query : str
            Lookup query.

        Returns
        -------
        dict[str, Any]
            A dictionary with a `notes` field.
        """

        notes = f"Notes about {query}: ... (demo content from {self.source})"
        return {"notes": notes}


def create_lookup_tool(**kwargs: Any) -> LookupTool:
    """Factory for `LookupTool`."""

    return LookupTool(**kwargs)


register_tool_factory(
    "lookup_tool", "ice_tools.generated.lookup_tool:create_lookup_tool"
)
