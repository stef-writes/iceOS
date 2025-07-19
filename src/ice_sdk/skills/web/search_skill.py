from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx
from pydantic import BaseModel, Field, model_validator

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["WebSearchSkill", "WebSearchConfig"]


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
    def _populate_key(cls, values):  # noqa: N805 – pydantic API
        if not values.api_key:
            env_key = os.getenv("SERPAPI_KEY")
            if env_key:
                values.api_key = env_key  # type: ignore[assignment]
        if not values.api_key:
            raise ValueError("SerpAPI API key must be provided via config or env var")
        return values


class WebSearchSkill(SkillBase):
    """Search the public web via SerpAPI and return simplified organic results.

    Example
    -------
    >>> import asyncio, os
    >>> os.environ["SERPAPI_KEY"] = "test-123"
    >>> skill = WebSearchSkill()
    >>> asyncio.run(skill.execute({"query": "openai"}))  # doctest: +SKIP
    {"results": [{"title": "OpenAI", "link": "https://openai.com", ...}]}
    """

    name: str = "web_search"
    description: str = (
        "Search the public web via SerpAPI and return the top organic results."
    )

    # Concrete config instance (avoid FieldInfo when SkillBase is *not* a Pydantic model)
    config: WebSearchConfig = WebSearchConfig()

    # ---------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------
    async def _execute_impl(
        self,
        *,
        query: str | None = None,
        num: int | None = None,
        input_data: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # Accept legacy *input_data* mapping.
        if query is None and input_data is not None:
            query = str(input_data.get("query", "")).strip()

        if num is None and input_data is not None:
            num = int(input_data.get("num", self.config.num_results))

        query = (query or "").strip()
        if not query:
            raise SkillExecutionError("'query' parameter is required")

        n: int = num or self.config.num_results

        params: Dict[str, Any] = {
            "q": query,
            "api_key": self.config.api_key,
            "num": n,
            "engine": "google",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://serpapi.com/search.json", params=params)

        if resp.status_code != 200:
            snippet = resp.text[:200]
            raise SkillExecutionError(f"SerpAPI error {resp.status_code}: {snippet}")

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
    def get_required_config(self):  # noqa: D401 – simple method name
        return ["api_key"]
