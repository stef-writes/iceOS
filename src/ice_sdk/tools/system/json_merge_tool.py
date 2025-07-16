from __future__ import annotations

"""Merge multiple JSON documents (deep merge).

Later documents take precedence over earlier keys recursively.  Non-dict values
are overwritten directly.  Example:

    >>> JSONMergeTool().run(docs=[{"a": 1, "b": {"x": 1}}, {"b": {"y": 2}}])
    {"merged": {"a": 1, "b": {"x": 1, "y": 2}}}
"""

from typing import Any, ClassVar, Dict, List  # noqa: E402

from ..base import BaseTool, ToolError  # noqa: E402

__all__ = ["JSONMergeTool"]


class JSONMergeTool(BaseTool):
    """Deep-merge a list of JSON objects (dicts)."""

    name: ClassVar[str] = "json_merge"
    description: ClassVar[str] = "Deep-merge multiple JSON documents."
    tags: ClassVar[List[str]] = ["json", "merge", "utility"]

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "docs": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of JSON objects to merge (later wins)",
            }
        },
        "required": ["docs"],
    }

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {"merged": {"type": "object", "description": "Merged document"}},
        "required": ["merged"],
    }

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------

    @staticmethod
    def _deep_merge(
        a: Dict[str, Any], b: Dict[str, Any]
    ) -> Dict[str, Any]:  # noqa: D401
        """Return *a* merged into *b* (b has precedence)."""

        out = a.copy()
        for key, b_val in b.items():
            if key in out and isinstance(out[key], dict) and isinstance(b_val, dict):
                out[key] = JSONMergeTool._deep_merge(out[key], b_val)
            else:
                out[key] = b_val
        return out

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        docs = kwargs.get("docs")
        if not isinstance(docs, list):
            raise ToolError("'docs' must be a list of JSON objects")

        merged: Dict[str, Any] = {}
        for idx, doc in enumerate(docs):
            if not isinstance(doc, dict):
                raise ToolError(f"docs[{idx}] is not an object")
            merged = self._deep_merge(merged, doc)
        return {"merged": merged}
