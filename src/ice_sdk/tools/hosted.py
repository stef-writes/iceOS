"""Hosted tools implementation."""
from typing import Any, ClassVar, Dict, List, TypedDict
import os
import asyncio
import httpx

from .base import BaseTool, ToolError


class SearchResult(TypedDict):
    """Typed dict returned by the search tool."""

    title: str
    url: str
    snippet: str


class WebSearchTool(BaseTool):
    """Tool for searching the web."""
    name: ClassVar[str] = "web_search"
    description: ClassVar[str] = "Search the web for information"
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "user_location": {
                "type": "object",
                "properties": {
                    "country": {"type": "string"}
                }
            },
            "search_context_size": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "default": "medium"
            }
        },
        "required": ["query"]
    }

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        """Execute web search.
        
        Args:
            query: Search query
            user_location: Optional user location
            search_context_size: Amount of context to use
        """
        query: str = kwargs.get("query")  # type: ignore[assignment]
        if not query:
            raise ToolError("'query' argument is required")

        user_location = kwargs.get("user_location", {})  # type: ignore[assignment]
        search_context_size = kwargs.get("search_context_size", "medium")

        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            raise ToolError("Environment variable SERPAPI_KEY is not set")

        # Map search_context_size → SerpAPI "num" parameter (max 100)
        num_map = {"low": 5, "medium": 10, "high": 20}
        num_results = num_map.get(search_context_size, 10)

        params = {
            "api_key": api_key,
            "engine": "google",
            "q": query,
            "num": num_results,
        }

        if country := user_location.get("country"):
            params["gl"] = country

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get("https://serpapi.com/search.json", params=params)
                res.raise_for_status()
                payload = res.json()
        except Exception as exc:  # pragma: no cover – network issues, etc.
            raise ToolError(f"Web search failed: {exc}") from exc

        results: List[SearchResult] = []
        for item in payload.get("organic_results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                }
            )

        return {"results": results}

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
                "description": "IDs of vector stores to search"
            },
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_num_results": {
                "type": "integer",
                "description": "Maximum number of results"
            },
            "include_search_results": {
                "type": "boolean",
                "default": False
            }
        },
        "required": ["vector_store_ids", "query"]
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
                raise ToolError(f"Vector store query failed for collection '{cid}': {exc}") from exc

            ids = res.get("ids", [[]])[0]
            dists = res.get("distances", [[]])[0]
            metas = res.get("metadatas", [[]])[0]

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

from pydantic import ConfigDict


class ComputerTool(BaseTool):
    """Tool for controlling a virtual computer."""
    name: ClassVar[str] = "computer"
    description: ClassVar[str] = "Control a virtual computer"
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["click", "type", "scroll", "screenshot"],
                "description": "Action to perform"
            },
            "x": {
                "type": "integer",
                "description": "X coordinate for click/scroll"
            },
            "y": {
                "type": "integer",
                "description": "Y coordinate for click/scroll"
            },
            "text": {
                "type": "string",
                "description": "Text to type"
            }
        },
        "required": ["action"]
    }

    # Allow dynamic attribute assignment (e.g. self.dimensions)
    model_config: ClassVar = ConfigDict(extra="allow")  # type: ignore[var-annotated]

    def __init__(self, dimensions: tuple[int, int] = (1280, 720)):
        """Initialize computer tool.
        
        Args:
            dimensions: Screen dimensions (width, height)
        """
        super().__init__()
        self.dimensions = dimensions

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        """Execute computer action.
        
        Args:
            action: Action to perform
            x: X coordinate
            y: Y coordinate
            text: Text to type
        """
        import base64
        import io

        action = kwargs.get("action")
        if action not in {"click", "type", "scroll", "screenshot"}:
            raise ToolError("Unsupported action for computer tool")

        try:
            import pyautogui  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ToolError("'pyautogui' package is required for ComputerTool") from exc

        try:
            if action == "click":
                x = kwargs.get("x")
                y = kwargs.get("y")
                if x is None or y is None:
                    raise ToolError("'click' requires 'x' and 'y' coordinates")
                await asyncio.to_thread(pyautogui.click, x, y)  # type: ignore[arg-type]
                return {"success": True}

            if action == "type":
                text = kwargs.get("text")
                if text is None:
                    raise ToolError("'type' requires 'text'")
                await asyncio.to_thread(pyautogui.typewrite, str(text))  # type: ignore[arg-type]
                return {"success": True}

            if action == "scroll":
                x = kwargs.get("x", 0)
                y = kwargs.get("y")
                if y is None:
                    raise ToolError("'scroll' requires 'y' delta")
                await asyncio.to_thread(pyautogui.scroll, y, x=x)  # type: ignore[arg-type]
                return {"success": True}

            if action == "screenshot":
                img = await asyncio.to_thread(pyautogui.screenshot)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode()
                return {"image_base64": encoded}
        except Exception as exc:  # pragma: no cover – runtime errors
            raise ToolError(f"Computer action failed: {exc}") from exc

        return {"success": False} 