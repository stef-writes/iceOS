from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel

from ice_builder.retrieval.blueprints_adapter import list_blueprints
from ice_builder.retrieval.library_api_adapter import list_library_assets_via_api
from ice_builder.retrieval.registry_adapter import list_tool_schemas
from ice_builder.retrieval.runs_adapter import list_recent_runs


class RetrievalFacade(BaseModel):
    """Compose retrieval adapters behind a simple interface."""

    async def fetch_context(self, *, query: str | None = None) -> Dict[str, Any]:
        tools = await list_tool_schemas()
        lib = await list_library_assets_via_api(prefix=query)
        bps = await list_blueprints()
        rns = await list_recent_runs()
        return {"tools": tools, "library": lib, "blueprints": bps, "runs": rns}
