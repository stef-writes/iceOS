"""Vector search tool for ChromaDB integration."""

from __future__ import annotations

import asyncio
import os
from typing import Any, ClassVar, Dict, List

from ..base import BaseTool, ToolError


class FileSearchTool(BaseTool):
    """Tool for searching through vector stores."""

    name: ClassVar[str] = "file_search"
    description: ClassVar[str] = "Search through vector stores"
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "vector_store_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "IDs of vector stores to search",
            },
            "query": {"type": "string", "description": "Search query"},
            "max_num_results": {
                "type": "integer",
                "description": "Maximum number of results",
            },
            "include_search_results": {"type": "boolean", "default": False},
        },
        "required": ["vector_store_ids", "query"],
    }
    tags: ClassVar[List[str]] = ["data", "vector", "search"]

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {"type": "object"},
            },
            "ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "oneOf": [
            {"required": ["results"]},
            {"required": ["ids"]},
        ],
    }

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        """Execute file search.

        Args:
            vector_store_ids: IDs of vector stores to search
            query: Search query
            max_num_results: Maximum number of results
            include_search_results: Whether to include results in output
        """
        from decimal import Decimal

        # Lazy import to keep Chroma optional --------------------------------
        try:
            import chromadb  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ToolError(
                "'chromadb' package is required for FileSearchTool. Install with `pip install chromadb`."
            ) from exc

        vector_store_ids = kwargs.get("vector_store_ids")
        query = kwargs.get("query")
        if not vector_store_ids or not isinstance(vector_store_ids, list):
            raise ToolError("'vector_store_ids' must be a list of collection names")
        if not query:
            raise ToolError("'query' argument is required")

        max_num_results: int = kwargs.get("max_num_results", 5)
        include_results: bool = kwargs.get("include_search_results", False)

        # Instantiate client in a worker thread – disk I/O can be slow
        client = await asyncio.to_thread(
            chromadb.PersistentClient,
            path=os.getenv("CHROMA_PATH", "./chromadb"),
        )  # type: ignore

        aggregate_matches: list[dict[str, Any]] = []
        for cid in vector_store_ids:
            try:
                coll = await asyncio.to_thread(client.get_or_create_collection, name=cid)  # type: ignore[attr-defined]
                res = await asyncio.to_thread(
                    coll.query, query_texts=[query], n_results=max_num_results
                )  # type: ignore[attr-defined]
            except Exception as exc:  # pragma: no cover – collection issues
                raise ToolError(
                    f"Vector store query failed for collection '{cid}': {exc}"
                ) from exc

            ids = res.get("ids", [[]])[0]  # type: ignore[index]
            dists = res.get("distances", [[]])[0]  # type: ignore[index]
            metas = res.get("metadatas", [[]])[0]  # type: ignore[index]

            for idx, _id in enumerate(ids):
                aggregate_matches.append(
                    {
                        "collection": cid,
                        "id": _id,
                        "score": float(Decimal(str(dists[idx]))),
                        "metadata": metas[idx] if idx < len(metas) else {},
                    }
                )

        # Sort all matches by score ascending (Chroma uses distance)
        aggregate_matches.sort(key=lambda m: m["score"])

        if include_results:
            return {"results": aggregate_matches[:max_num_results]}
        return {"ids": [m["id"] for m in aggregate_matches[:max_num_results]]}
