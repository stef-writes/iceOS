from __future__ import annotations

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.anyio


async def test_suggest_applies_policy_overrides() -> None:
    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": "Bearer dev-token"}
    body = {
        "text": "hello",
        "canvas_state": {},
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        r = await c.post("/api/v1/builder/suggest", headers=headers, json=body)
        assert r.status_code == 200, r.text
        # On success, we don't assert patches, only that request succeeded and didn't 4xx
