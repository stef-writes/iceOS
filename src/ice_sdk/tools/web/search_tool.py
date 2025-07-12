"""Web search tool using SerpAPI."""

from __future__ import annotations

import os
from typing import Any, ClassVar, Dict, List, TypedDict

import httpx

from ..base import BaseTool, ToolError


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
                "properties": {"country": {"type": "string"}},
            },
            "search_context_size": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "default": "medium",
            },
        },
        "required": ["query"],
    }
    tags: ClassVar[List[str]] = ["web", "search", "information"]

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "snippet": {"type": "string"},
                    },
                    "required": ["title", "url"],
                },
            }
        },
        "required": ["results"],
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
                # *params* includes booleans & ints – acceptable to httpx but mypy's narrow type
                res = await client.get(
                    "https://serpapi.com/search.json",
                    params=params,  # type: ignore[arg-type]
                )
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
