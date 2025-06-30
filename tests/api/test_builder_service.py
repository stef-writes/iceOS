from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_builder_happy_path():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Start draft
        resp = await client.post("/api/v1/builder/start", json={"total_nodes": 1, "name": "demo"})
        assert resp.status_code == 201
        data = resp.json()
        draft_id = data["draft_id"]
        q = data["question"]
        assert q["key"] == "persist"

        # Answer persist
        resp = await client.post(
            "/api/v1/builder/answer",
            json={"draft_id": draft_id, "key": "persist", "answer": "y"},
        )
        assert resp.status_code == 200
        q = resp.json()["next_question"]
        assert q["key"] == "type"

        # Answer type
        resp = await client.post(
            "/api/v1/builder/answer",
            json={"draft_id": draft_id, "key": "type", "answer": "tool"},
        )
        assert resp.status_code == 200
        q = resp.json()["next_question"]
        assert q["key"] == "name"

        # Answer name
        resp = await client.post(
            "/api/v1/builder/answer",
            json={"draft_id": draft_id, "key": "name", "answer": "demo_tool"},
        )
        assert resp.status_code == 200
        q = resp.json()["next_question"]
        assert q is None or q["key"] in {"model", "deps", "adv"}

        # If model question present, answer it
        if q and q["key"] == "model":
            await client.post(
                "/api/v1/builder/answer",
                json={"draft_id": draft_id, "key": "model", "answer": "gpt-3.5-turbo"},
            )
            # Fetch next question which could be deps
            q_resp = await client.post(
                "/api/v1/builder/answer",
                json={"draft_id": draft_id, "key": "deps", "answer": ""},
            )
            assert q_resp.status_code in {200, 204, 201, 202}

        # If deps question present, answer it
        if q and q["key"] == "deps":
            await client.post(
                "/api/v1/builder/answer",
                json={"draft_id": draft_id, "key": "deps", "answer": ""},
            )

        # Answer advanced settings question (skip) --------------------
        await client.post(
            "/api/v1/builder/answer",
            json={"draft_id": draft_id, "key": "adv", "answer": "n"},
        )

        # Render chain
        resp = await client.get("/api/v1/builder/render", params={"draft_id": draft_id})
        assert resp.status_code == 200
        source = resp.json()["source"]
        assert "ScriptChain" in source

        # New field – Mermaid graph
        mermaid = resp.json()["mermaid"]
        assert mermaid.startswith("graph LR")

        # Delete draft
        resp = await client.delete(f"/api/v1/builder/{draft_id}")
        assert resp.status_code == 204 