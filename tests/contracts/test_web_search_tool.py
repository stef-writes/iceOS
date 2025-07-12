from __future__ import annotations

import os
from typing import Any

import pytest  # type: ignore

try:
    import respx  # type: ignore
except ModuleNotFoundError:
    pytest.skip("respx not installed", allow_module_level=True)

from ice_sdk.tools.web.search_tool import WebSearchTool


@pytest.mark.contract
@pytest.mark.asyncio
async def test_web_search_tool_mocked_serpapi() -> None:
    """WebSearchTool should parse results from SerpAPI payload."""

    # Set dummy API key ---------------------------------------------------
    os.environ["SERPAPI_KEY"] = "test-123"

    dummy_payload: dict[str, Any] = {
        "organic_results": [
            {
                "title": "Example",
                "link": "https://example.com",
                "snippet": "Lorem ipsum",
            }
        ]
    }

    with respx.mock(base_url="https://serpapi.com") as mock:
        mock.get("/search.json").respond(200, json=dummy_payload)

        tool = WebSearchTool()
        result: Any = await tool.run(query="hello world")

        assert "results" in result
        assert result["results"][0]["title"] == "Example"  # type: ignore[index]
