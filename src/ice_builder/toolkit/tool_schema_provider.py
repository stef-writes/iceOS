from __future__ import annotations

from typing import Any, Dict, Tuple

from pydantic import BaseModel

from ice_core.services.tool_service import ToolService
from ice_core.utils.node_conversion import discover_tool_schemas


class ToolSchemaProvider(BaseModel):
    """Provide tool input/output schemas for builder planning.

    Uses the stable ``ToolService`` facade and schema discovery utilities in
    ``ice_core``. This avoids direct dependency on orchestrator internals.

    Methods are synchronous where possible to keep call-sites simple.
    """

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        svc = ToolService()
        return svc.list_tools()

    def get_tool_schemas(self, tool_name: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Return (input_schema, output_schema) for a tool name."""
        return discover_tool_schemas(tool_name)
