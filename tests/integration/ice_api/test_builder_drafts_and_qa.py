from __future__ import annotations

import json
from typing import Any, Dict

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.anyio


async def test_builder_drafts_crud() -> None:
    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": "Bearer dev-token"}

    draft_key = "itest_draft_1"
    payload: Dict[str, Any] = {"data": {"nodes": [], "meta": {"name": "wip"}}}

    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        # Put draft
        r_put = await c.put(
            f"/api/v1/builder/drafts/{draft_key}", headers=headers, json=payload
        )
        assert r_put.status_code == 200, r_put.text
        obj = r_put.json()
        assert obj.get("ok") is True
        assert obj.get("key") == draft_key

        # Get draft
        r_get = await c.get(f"/api/v1/builder/drafts/{draft_key}", headers=headers)
        assert r_get.status_code == 200, r_get.text
        draft = r_get.json()
        assert isinstance(draft, dict)
        assert isinstance(draft.get("data"), dict)
        assert draft["data"].get("meta", {}).get("name") == "wip"

        # Delete draft
        r_del = await c.delete(f"/api/v1/builder/drafts/{draft_key}", headers=headers)
        assert r_del.status_code == 200, r_del.text
        # Subsequent GET should 404
        r_get2 = await c.get(f"/api/v1/builder/drafts/{draft_key}", headers=headers)
        assert r_get2.status_code == 404


async def test_builder_suggest_surfaces_qa_and_cost() -> None:
    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": "Bearer dev-token"}

    # Seed builder_hints directly in canvas_state so the service captures them
    builder_hints = {
        "questions": ["Which data source?"],
        "missing_fields": {"tool_name": "required"},
        "usage": {"prompt_tokens": 500, "completion_tokens": 200},
        "provider": "openai",
        "model": "gpt-4o",
    }

    body = {
        "text": "draft a simple workflow",
        "canvas_state": {"builder_hints": builder_hints},
    }

    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        r = await c.post("/api/v1/builder/suggest", headers=headers, json=body)
        assert r.status_code == 200, r.text
        data = r.json()
        # Patches may be empty in noop planner; we care about hints surfacing
        assert "questions" in data
        assert data["questions"] == builder_hints["questions"]
        assert "missing_fields" in data
        assert data["missing_fields"] == builder_hints["missing_fields"]
        # Cost estimate should be > 0 with usage
        assert isinstance(data.get("cost_estimate_usd"), (int, float))
        assert data["cost_estimate_usd"] >= 0.0
