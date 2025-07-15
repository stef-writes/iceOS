"""Web search tool powered by SerpAPI.

This tool enables agents and workflow nodes to query the public web via the
SerpAPI service.  The implementation abides by the project rules:

1. Uses full type hints and Pydantic models via the *BaseTool* base-class.
2. Performs all network I/O inside *run* keeping external side-effects localised.
3. Exposes an idempotent *runtime_validate* hook (inherited, no custom state).
4. Raises a typed *ToolError* on failure conditions.

The corresponding contract tests live in ``tests/contracts/test_web_search_tool.py``.
"""

from __future__ import annotations

import os
from typing import Any, ClassVar, Dict, List

import httpx

from ..base import BaseTool, ToolError

__all__ = ["WebSearchTool"]


class WebSearchTool(BaseTool):
    """Query Google search results via SerpAPI and return a simplified list.

    Example
    -------
    >>> import os, asyncio
    >>> os.environ["SERPAPI_KEY"] = "test-123"
    >>> tool = WebSearchTool()
    >>> asyncio.run(tool.run(query="openai"))  # doctest: +SKIP
    {"results": [{"title": "OpenAI", "link": "https://openai.com", ...}]}
    """

    # ------------------------------------------------------------------
    # Static metadata ---------------------------------------------------
    # ------------------------------------------------------------------

    name: ClassVar[str] = "web_search"
    description: ClassVar[str] = (
        "Search the public web via SerpAPI and return the top organic results."
    )

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 10,
                "description": "Number of results to return (<=20)",
            },
        },
        "required": ["query"],
    }

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "link": {"type": "string"},
                        "snippet": {"type": "string"},
                    },
                    "required": ["title", "link"],
                },
            }
        },
        "required": ["results"],
    }

    # Capability taxonomy -----------------------------------------------------
    tags: ClassVar[List[str]] = ["web", "search", "io"]

    # ------------------------------------------------------------------
    # Business logic ----------------------------------------------------
    # ------------------------------------------------------------------

    async def run(self: "WebSearchTool", **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        """Execute the web search.

        Parameters
        ----------
        query : str
            The search phrase.
        num : int, optional
            Desired number of results (default: 10, max 20).

        Returns
        -------
        dict
            {"results": [{"title": str, "link": str, "snippet": str}]}
        """

        # Validate & extract parameters ----------------------------------
        self.validate_params(kwargs)

        query: str = kwargs["query"]
        num: int = kwargs.get("num", 10)

        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            raise ToolError("SERPAPI_KEY environment variable not set")

        params: Dict[str, Any] = {
            "q": query,
            "api_key": api_key,
            "num": num,
            "engine": "google",
        }

        # Network I/O ----------------------------------------------------
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://serpapi.com/search.json", params=params)

            if resp.status_code != 200:  # pragma: no cover – network failure
                snippet = resp.text[:200]
                raise ToolError(f"SerpAPI error {resp.status_code}: {snippet}")

            payload = resp.json()

        organic: List[Dict[str, Any]] = payload.get("organic_results", [])

        simplified: List[Dict[str, str]] = [
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in organic[:num]
        ]

        return {"results": simplified}
