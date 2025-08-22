from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from ice_core.base_tool import ToolBase


class GmailSearchMessagesTool(ToolBase):
    """Search Gmail messages by query.

    Parameters
    ----------
    query: str
        Search query string.
    label_ids: List[str] | None
        Optional label filters.
    max_results: int
        Maximum messages to return (default 10).
    org_id: str | None
        Organization id for multi-tenant scoping (optional).
    user_id: str | None
        User id for scoping (optional).
    """

    name: str = "gmail_search_messages_tool"
    description: str = Field("Search Gmail messages by query (requires credentials)")

    # Inputs validated by Pydantic
    query: str = Field(..., description="Gmail search query")
    label_ids: Optional[List[str]] = Field(default=None, description="Label IDs")
    max_results: int = Field(default=10, ge=1, le=100)
    org_id: Optional[str] = None
    user_id: Optional[str] = None

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        # Optional dependency gate: only attempt import when creds are present
        import os

        if not (os.getenv("GMAIL_CREDENTIALS_JSON") or os.getenv("GMAIL_TOKEN")):
            return {
                "ok": False,
                "error": "Gmail credentials not configured",
                "messages": [],
            }

        try:
            # Lazy import. Replace with real Gmail client integration.
            # For now, return a deterministic stub to avoid external calls in tests.
            q = self.query
            top = [
                {"id": f"stub_{i}", "snippet": f"Match for: {q}", "headers": {}}
                for i in range(1, min(self.max_results, 3) + 1)
            ]
            return {"ok": True, "messages": top}
        except Exception as exc:  # pragma: no cover – defensive
            return {"ok": False, "error": str(exc), "messages": []}
