from __future__ import annotations

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.anyio


async def test_preview_denies_import_os() -> None:
    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": "Bearer dev-token"}
    body = {
        "language": "python",
        "code": "import os\nresult = os.listdir('/')",
        "inputs": {},
    }
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        r = await c.post("/api/v1/builder/preview/tool", headers=headers, json=body)
        assert r.status_code == 400, r.text
        data = r.json()
        assert "detail" in data


async def test_preview_allows_safe_json() -> None:
    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": "Bearer dev-token"}
    body = {
        "language": "python",
        "code": "import json\nresult = json.loads('123')",
        "inputs": {},
    }
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        r = await c.post("/api/v1/builder/preview/tool", headers=headers, json=body)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("success") is True
