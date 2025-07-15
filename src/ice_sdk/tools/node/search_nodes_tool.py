"""search_nodes – retrieve similar nodes by semantic query.

Returns a list of `node_id` strings ranked by cosine similarity against
a vector index built from blueprint / canvas metadata.
"""

from __future__ import annotations

from typing import List

from ice_sdk.providers.vector.node_index import NodeIndex
from ice_sdk.tools.base import BaseTool, ToolContext

# Global singleton index (in-memory)
_NODE_INDEX: NodeIndex | None = None


def _get_index() -> NodeIndex:
    global _NODE_INDEX
    if _NODE_INDEX is None:
        _NODE_INDEX = NodeIndex()
    return _NODE_INDEX


class SearchNodesTool(BaseTool):
    """Semantic node search.

    Args:
        query: Natural-language query or node snippet.
        k:     Number of similar nodes to return (default 5).
    Returns:
        List of `node_id` strings.
    """

    name = "search_nodes"
    description = "Return up to *k* node_ids most semantically similar to *query*."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "k": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    }
    output_schema = {"type": "array", "items": {"type": "string"}}

    async def run(self, ctx: ToolContext, query: str, k: int = 5) -> List[str]:  # type: ignore[override]
        index = _get_index()
        return index.search(query, k=k)
