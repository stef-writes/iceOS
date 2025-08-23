from __future__ import annotations

import json

from starlette.testclient import TestClient

from ice_api.main import app


def test_rest_registered_blueprint_then_run_by_id() -> None:
    client = TestClient(app)

    # Create a minimal blueprint via REST (DB authoritative)
    bp = {
        "schema_version": "1.2.0",
        "metadata": {"name": "reg_demo"},
        "nodes": [
            {
                "id": "llm1",
                "type": "llm",
                "provider": "openai",
                "model": "gpt-4o",
                "prompt": "Say hello.",
            }
        ],
    }

    r = client.post(
        "/api/v1/blueprints/",
        headers={
            "Authorization": "Bearer dev-token",
            "Content-Type": "application/json",
            "X-Version-Lock": "__new__",
        },
        data=json.dumps(bp),
    )
    assert r.status_code in (200, 201), r.text
    bp_id = r.json()["id"]

    # Start execution via REST by-reference; allow short wait
    run = client.post(
        "/api/v1/executions/?wait_seconds=5",
        headers={
            "Authorization": "Bearer dev-token",
            "Content-Type": "application/json",
        },
        json={"blueprint_id": bp_id, "inputs": {}},
    )
    assert run.status_code in (200, 202), run.text
    data = run.json()
    # Either terminal or accepted (depending on timing)
    assert data.get("status") in {"accepted", "completed", "failed"}
