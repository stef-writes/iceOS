import os
import asyncio
from unittest import mock

import httpx
import pytest

from ice_sdk.skills.web import WebSearchSkill


@pytest.mark.asyncio
async def test_web_search_skill_exec(monkeypatch):
    # Arrange
    monkeypatch.setenv("SERPAPI_KEY", "test")
    skill = WebSearchSkill()

    # Monkeypatch HTTP call
    async def fake_get(self, url: str, params: dict |
                       None = None):  # noqa: D401, ANN001, E501
        class _Resp:
            status_code = 200

            @staticmethod
            def json():
                return {
                    "organic_results": [
                        {
                            "title": "Foo",
                            "link": "https://example.com",
                            "snippet": "bar",
                        }
                    ]
                }

        return _Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)  # type: ignore[arg-type]

    # Act
    res = await skill.execute({"query": "foo"})

    # Assert
    assert "results" in res
    assert res["results"][0]["title"] == "Foo" 