from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from ice_core.base_tool import ToolBase


class LookupTool(ToolBase):
    name: str = "lookup_tool"
    description: str = Field("Return concise notes for a query")
    source: str = Field("demo", description="Source label")

    async def _execute_impl(self, *, query: str) -> Dict[str, Any]:
        notes = f"Notes about {query}: ... (demo content from {self.source})"
        return {"notes": notes}


def create_lookup_tool(**kwargs: Any) -> LookupTool:
    return LookupTool(**kwargs)
