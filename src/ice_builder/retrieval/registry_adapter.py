from __future__ import annotations

from typing import Any, Dict, List

from ice_core.unified_registry import registry


async def list_tool_schemas() -> List[Dict[str, Any]]:
    """Return tool schemas from the unified registry (minimal form)."""
    names = registry.list_tools()
    # Minimal schema-only view (lazy; callers can resolve more later)
    return [{"name": n} for n in names]


__all__ = ["list_tool_schemas"]
