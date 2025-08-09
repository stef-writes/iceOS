"""SearchTool – SerpAPI-backed web search with deterministic fallback.

External side-effects are confined to this Tool implementation per project rules.
If SERPAPI_KEY is set in the environment, performs a live query; otherwise returns
a stable, deterministic result so tests remain offline.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx
from pydantic import Field

from ice_core.base_tool import ToolBase
from ice_core.unified_registry import register_tool_factory


class SearchTool(ToolBase):
    """Web search tool using SerpAPI when available.

    Parameters
    ----------
    engine : str
        Search engine (default: "google").
    num_results : int
        Number of results to return (default: 3).
    """

    name: str = "search_tool"
    description: str = Field(
        default="Search the web for a query (SerpAPI when configured; else deterministic)",
    )
    engine: str = Field(default="google")
    num_results: int = Field(default=3, ge=1, le=10)

    async def _execute_impl(self, *, query: str) -> Dict[str, Any]:  # noqa: D401
        """Return a list of search results for the given query.

        Returns a dict with a `results: List[dict]` payload where each entry contains
        `title`, `link` and `snippet`.
        """

        api_key = os.getenv("SERPAPI_KEY") or os.getenv("SERPAPI_API_KEY")
        if api_key:
            try:
                params = {
                    "engine": self.engine,
                    "q": query,
                    "api_key": api_key,
                    "num": str(self.num_results),
                }
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.get("https://serpapi.com/search.json", params=params)
                    r.raise_for_status()
                    data = r.json()
            except Exception as exc:
                # Fail closed to deterministic fallback
                return {
                    "results": [
                        {
                            "title": f"About {query}",
                            "link": f"https://example.com/{query.replace(' ', '-').lower()}",
                            "snippet": f"Deterministic fallback for '{query}' (error: {str(exc)})",
                        }
                    ]
                }

            results: List[Dict[str, Any]] = []
            # Prefer organic_results when present
            for item in (data.get("organic_results") or [])[: self.num_results]:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                    }
                )
            if not results:
                # Fallback when response shape differs
                results = [
                    {
                        "title": f"About {query}",
                        "link": f"https://example.com/{query.replace(' ', '-').lower()}",
                        "snippet": f"Deterministic fallback for '{query}' (no results)",
                    }
                ]
            return {"results": results}

        # Deterministic offline fallback
        return {
            "results": [
                {
                    "title": f"About {query}",
                    "link": f"https://example.com/{query.replace(' ', '-').lower()}",
                    "snippet": f"Deterministic offline result for '{query}'",
                }
            ]
        }


def create_search_tool(**kwargs: Any) -> SearchTool:
    return SearchTool(**kwargs)


register_tool_factory("search_tool", "ice_tools.generated.search_tool:create_search_tool")

