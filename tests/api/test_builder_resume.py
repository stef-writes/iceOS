import json

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_builder_export_resume_roundtrip():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Start new draft --------------------------------------------------
        resp = await client.post("/api/v1/builder/start", json={"total_nodes": 1, "name": "resume_demo"})
        assert resp.status_code == 201
        data = resp.json()
        draft_id = data["draft_id"]

        # Answer first (and only) question prompts -----------------------
        await client.post(
            "/api/v1/builder/answer",
            json={"draft_id": draft_id, "key": "type", "answer": "tool"},
        )
        await client.post(
            "/api/v1/builder/answer",
            json={"draft_id": draft_id, "key": "name", "answer": "demo_tool"},
        )
        # Depending on engine flow, there might be deps step now ----------
        next_q_resp = await client.get("/api/v1/builder/next", params={"draft_id": draft_id})
        if next_q_resp.json() and next_q_resp.json().get("key") == "deps":
            await client.post(
                "/api/v1/builder/answer",
                json={"draft_id": draft_id, "key": "deps", "answer": ""},
            )

        # Export current draft ------------------------------------------
        export_resp = await client.get("/api/v1/builder/export", params={"draft_id": draft_id})
        assert export_resp.status_code == 200
        draft_payload = export_resp.json()["draft"]
        assert "nodes" in draft_payload and draft_payload["nodes"]

        # Resume from exported draft ------------------------------------
        resume_resp = await client.post("/api/v1/builder/resume", json={"draft": draft_payload})
        assert resume_resp.status_code == 201
        new_draft_id = resume_resp.json()["draft_id"]
        assert new_draft_id != draft_id

        # Ensure we can continue interaction ----------------------------
        q_resp = await client.get("/api/v1/builder/next", params={"draft_id": new_draft_id})
        # Next question may be None if completed; just ensure endpoint works
        assert q_resp.status_code == 200 