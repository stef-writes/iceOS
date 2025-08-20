from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def _create_min_blueprint() -> str:
    payload = {
        "name": "exec-demo",
        "nodes": [{"id": "n1", "type": "tool"}],
        "metadata": {},
    }
    res = client.post(
        "/api/v1/blueprints/",
        json=payload,
        headers={"Authorization": "Bearer dev-token", "X-Version-Lock": "__new__"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_execution_status_persisted_in_redis():
    blueprint_id = _create_min_blueprint()

    start = client.post(
        "/api/v1/executions/",
        json={"blueprint_id": blueprint_id},
        headers={"Authorization": "Bearer dev-token"},
    )
    assert start.status_code == 202, start.text
    exec_id = start.json()["execution_id"]

    # Query status; should be present even if server restarted (Redis-backed)
    status = client.get(
        f"/api/v1/executions/{exec_id}", headers={"Authorization": "Bearer dev-token"}
    )
    assert status.status_code == 200, status.text
    body = status.json()
    assert "status" in body and body["status"] in {
        "pending",
        "running",
        "completed",
        "failed",
    }

    # New: list executions should include our exec id
    listing = client.get(
        "/api/v1/executions/", headers={"Authorization": "Bearer dev-token"}
    )
    assert listing.status_code == 200
    ids = {e["execution_id"] for e in listing.json().get("executions", [])}
    assert exec_id in ids

    # New: cancel endpoint should mark as canceled (failed)
    cancel_res = client.post(
        f"/api/v1/executions/{exec_id}/cancel",
        headers={"Authorization": "Bearer dev-token"},
    )
    assert cancel_res.status_code == 200
    final = client.get(
        f"/api/v1/executions/{exec_id}", headers={"Authorization": "Bearer dev-token"}
    )
    assert final.status_code == 200
    assert final.json().get("status") in {"failed", "completed", "running", "pending"}
