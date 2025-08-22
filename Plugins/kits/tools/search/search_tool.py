from __future__ import annotations

import os
from typing import Any, Dict, List, Literal

import httpx
from pydantic import Field

from ice_core.base_tool import ToolBase
from ice_core.exceptions import CoreError, ErrorCode


class SearchTool(ToolBase):
    name: str = "search_tool"
    description: str = Field(
        default="Search the web for a query using SerpAPI (live only)"
    )
    # Expose discrete engines to surface UI enum hints in the catalog
    engine: Literal["google", "bing", "duckduckgo"] = Field(
        default="google", description="Search engine provider"
    )
    num_results: int = Field(default=3, ge=1, le=10)

    async def _execute_impl(self, *, query: str) -> Dict[str, Any]:
        api_key = os.getenv("SERPAPI_KEY") or os.getenv("SERPAPI_API_KEY")
        if not api_key:
            raise CoreError(
                ErrorCode.UNKNOWN,
                "SearchTool requires SERPAPI_KEY (or SERPAPI_API_KEY) to be set",
            )

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
        except Exception as exc:  # pragma: no cover – network dependent
            raise CoreError(
                ErrorCode.UNKNOWN, f"SerpAPI request failed: {exc}"
            ) from exc

        results: List[Dict[str, Any]] = []
        for item in (data.get("organic_results") or [])[: self.num_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                }
            )
        return {"results": results}


def create_search_tool(**kwargs: Any) -> SearchTool:
    return SearchTool(**kwargs)
