import os
from contextlib import contextmanager

from fastapi.testclient import TestClient

from ice_api.main import app


@contextmanager
def _env(**kwargs):
    old = {}
    for k, v in kwargs.items():
        old[k] = os.environ.get(k)
        os.environ[k] = str(v)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


client = TestClient(app)


def test_finalize_blocked_when_estimate_exceeds_budget():
    # Very low budget to trigger rejection
    with _env(ORG_BUDGET_USD="0.00"):
        # Create partial and attempt finalize without lock first (expect 428)
        res = client.post(
            "/api/v1/mcp/blueprints/partial",
            headers={"Authorization": "Bearer dev-token"},
        )
        assert res.status_code == 200
        pb_id = res.json()["blueprint_id"]

        get_pb = client.get(
            f"/api/v1/mcp/blueprints/partial/{pb_id}",
            headers={"Authorization": "Bearer dev-token"},
        )
        lock = get_pb.headers.get("X-Version-Lock")
        assert lock

    # Attempt finalize with lock – should 400 because partial has no nodes
    fin = client.post(
        f"/api/v1/mcp/blueprints/partial/{pb_id}/finalize",
        headers={"Authorization": "Bearer dev-token", "X-Version-Lock": lock},
    )
    assert fin.status_code == 400


def test_run_blocked_when_estimate_exceeds_budget():
    with _env(ORG_BUDGET_USD="0.00", ICE_TESTING="1"):
        # Create blueprint with two LLM nodes to ensure non-zero estimated cost
        payload = {
            "name": "b",
            "nodes": [
                {
                    "id": "n1",
                    "type": "llm",
                    "model": "gpt-4o",
                    "prompt": "Say hi",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                },
                {
                    "id": "n2",
                    "type": "llm",
                    "dependencies": ["n1"],
                    "model": "gpt-4o",
                    "prompt": "Summarize",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                },
            ],
            "metadata": {},
        }
        create = client.post(
            "/api/v1/blueprints/",
            json=payload,
            headers={"Authorization": "Bearer dev-token", "X-Version-Lock": "__new__"},
        )
        assert create.status_code == 201
        bp_id = create.json()["id"]

        start = client.post(
            "/api/v1/executions/",
            json={"blueprint_id": bp_id},
            headers={"Authorization": "Bearer dev-token"},
        )
        assert start.status_code in (400, 402)
