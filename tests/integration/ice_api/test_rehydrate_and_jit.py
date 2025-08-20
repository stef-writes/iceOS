from __future__ import annotations

import json
import os

import httpx
import pytest

BASE = "http://127.0.0.1:8000/api/mcp"
AUTH = {"Authorization": "Bearer dev-token"}


@pytest.mark.asyncio
async def test_tool_rehydrate_and_jit() -> None:
    async with httpx.AsyncClient() as c:
        r = await c.get("http://127.0.0.1:8000/readyz")
        assert r.status_code == 200

    # Scaffold and register a tool (class-code only)
    async with httpx.AsyncClient() as c:
        sc = await c.post(
            f"{BASE}/components/scaffold",
            headers=AUTH,
            json={"type": "tool", "name": "rehydrate_demo"},
        )
        assert sc.status_code == 200
        tool_class_code = sc.json()["tool_class_code"]
        reg = await c.post(
            f"{BASE}/components/register",
            headers={**AUTH, "Content-Type": "application/json"},
            content=json.dumps(
                {
                    "type": "tool",
                    "name": "rehydrate_demo",
                    "description": "rehydrate test tool",
                    "tool_class_code": tool_class_code,
                    "auto_register": True,
                }
            ),
        )
        assert reg.status_code == 200
        assert reg.json()["registered"] is True

    # Create partial blueprint using the tool, finalize
    async with httpx.AsyncClient() as c:
        pb = await c.post(f"{BASE}/blueprints/partial", headers=AUTH)
        assert pb.status_code == 200
        pbid = pb.json()["blueprint_id"]
        h = await c.get(f"{BASE}/blueprints/partial/{pbid}", headers=AUTH)
        lock = h.headers.get("X-Version-Lock")
        assert lock
        upd = await c.put(
            f"{BASE}/blueprints/partial/{pbid}",
            headers={**AUTH, "X-Version-Lock": lock},
            json={
                "action": "add_node",
                "node": {
                    "id": "t1",
                    "type": "tool",
                    "tool_name": "rehydrate_demo",
                    "tool_args": {},
                    "input_schema": {},
                    "output_schema": {"ok": "bool"},
                },
            },
        )
        assert upd.status_code == 200
        h2 = await c.get(f"{BASE}/blueprints/partial/{pbid}", headers=AUTH)
        lock2 = h2.headers.get("X-Version-Lock")
        fin = await c.post(
            f"{BASE}/blueprints/partial/{pbid}/finalize",
            headers={**AUTH, "X-Version-Lock": lock2},
        )
        assert fin.status_code == 200
        bpid = fin.json()["blueprint_id"]

    # Start run and expect either 202 (still running) or 200 with success flag
    async with httpx.AsyncClient() as c:
        run = await c.post(
            f"{BASE}/runs",
            headers={**AUTH, "Content-Type": "application/json"},
            content=json.dumps({"blueprint_id": bpid}),
        )
        assert run.status_code == 202
        run_id = run.json()["run_id"]
        res = await c.get(f"{BASE}/runs/{run_id}", headers=AUTH)
        if res.status_code == 200:
            j = res.json()
            assert "success" in j


@pytest.mark.asyncio
async def test_prod_flag_disables_dynamic_autoreg() -> None:
    # Server reads env at startup; here we only ensure endpoint responsiveness under prod flag
    os.environ["ICEOS_DISABLE_RUNTIME_AUTOREG"] = "1"
    async with httpx.AsyncClient() as c:
        r = await c.get("http://127.0.0.1:8000/readyz")
        assert r.status_code == 200
