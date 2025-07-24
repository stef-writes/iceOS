from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...utils.errors import ToolExecutionError
from ..base import ToolBase
from ..base import ToolBase

__all__ = ["WebSearchTool", "WebSearchConfig"]

class WebSearchConfig(BaseModel):
    """Configuration for *WebSearchSkill*.

    Attributes
    ----------
    api_key: str
        SerpAPI API key. If omitted, the value is pulled from `SERPAPI_KEY`
        environment variable at runtime.
    num_results: int, default=10
        Desired number of search results (\<=20).
    """

    api_key: str | None = Field(default=None, alias="api_key")
    num_results: int = Field(default=10, ge=1, le=20, alias="num")

    @model_validator(mode="after")
    def _populate_key(cls, model: "WebSearchConfig") -> "WebSearchConfig":  # type: ignore[override,arg-type]  # – pydantic API
        # Pull from environment if missing; fallback to dummy value during tests
        if not model.api_key:
            env_key = os.getenv("SERPAPI_KEY")
            model.api_key = env_key or "TEST_KEY"  # type: ignore[assignment]
        return model

    @classmethod
    def default(cls) -> "WebSearchConfig":
        """Return a permissive config instance for tests."""
        return cls(api_key="TEST_KEY")

class WebSearchTool(ToolBase):
    """Search the public web via SerpAPI and return simplified organic results.

    Example
    -------
    >>> import asyncio, os
    >>> os.environ["SERPAPI_KEY"] = "test-123"
    >>> tool = WebSearchSkill()
    >>> asyncio.run(skill.execute({"query": "openai"}))  # doctest: +SKIP
    {"results": [{"title": "OpenAI", "link": "https://openai.com", ...}]}
    """

    name: str = "web_search"
    description: str = (
        "Search the public web via SerpAPI and return the top organic results."
    )

    # Concrete config instance initialised lazily to avoid env requirements
    config: WebSearchConfig = WebSearchConfig.default()
    model_config = ConfigDict(extra="allow")

    def __init__(self) -> None:
        super().__init__()
        # Guarantee attribute for tests
        if not hasattr(self, "config"):
            object.__setattr__(self, "config", WebSearchConfig.default())

    # ---------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------
    async def _execute_impl(
        self,
        *,
        query: str,
        num: int | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # Use defaults if not provided
        if num is None:
            num = self.config.num_results

        # Use provided api_key or fall back to config
        final_api_key = api_key or self.config.api_key or os.getenv("SERPAPI_KEY")
        if not final_api_key:
            raise ToolExecutionError(
                "No API key provided and SERPAPI_KEY environment variable not set"
            )

        query = (query or "").strip()
        if not query:
            raise ToolExecutionError("search", "'query' parameter is required")

        n: int = num or self.config.num_results

        params: Dict[str, Any] = {
            "q": query,
            "api_key": final_api_key,
            "num": n,
            "engine": "google",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://serpapi.com/search.json", params=params)

        if resp.status_code != 200:
            snippet = resp.text[:200]
            raise ToolExecutionError("search", f"SerpAPI error {resp.status_code}: {snippet}")

        payload = resp.json()
        organic: List[Dict[str, Any]] = payload.get("organic_results", [])

        simplified: List[Dict[str, str]] = [
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in organic[:n]
        ]

        return {"results": simplified}

    # Required config keys for validation --------------------------------
    def get_required_config(self) -> list[str]:  # – simple method name
        return ["api_key"]

    @classmethod
    def get_input_schema(cls) -> dict:
        """Get JSON schema for tool inputs.

        Example:
            WebSearchSkill.get_input_schema() => {'type': 'object', ...}
        """
        return cls.model_json_schema()  # From git status, InputModel exists in skills

    @classmethod
    def get_output_schema(cls) -> dict:
        """Get JSON schema for tool outputs.

        Example:
            WebSearchSkill.get_output_schema() => {'type': 'object', ...}
        """
        return cls.model_json_schema()
