from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def test_partial_blueprint_lock_and_finalize_flow():
    # create partial (no header needed for create; auth is global include)
    res = client.post(
        "/api/mcp/blueprints/partial",
        headers={"Authorization": "Bearer dev-token"},
    )
    assert res.status_code == 200, res.text
    partial = res.json()
    pb_id = partial["blueprint_id"]

    # initial update should fail without lock header
    upd = client.put(
        f"/api/mcp/blueprints/partial/{pb_id}",
        json={"action": "suggest"},
        headers={"Authorization": "Bearer dev-token"},
    )
    assert upd.status_code == 428

    # finalize requires lock as well
    fin = client.post(
        f"/api/mcp/blueprints/partial/{pb_id}/finalize",
        headers={"Authorization": "Bearer dev-token"},
    )
    assert fin.status_code == 428


def test_stateless_suggest_endpoint_readonly_and_commit():
    # create a new partial
    res = client.post(
        "/api/mcp/blueprints/partial",
        headers={"Authorization": "Bearer dev-token"},
    )
    assert res.status_code == 200, res.text
    partial = res.json()
    pb_id = partial["blueprint_id"]

    # Call stateless suggest (read-only)
    s1 = client.post(
        f"/api/mcp/blueprints/partial/{pb_id}/suggest",
        json={"top_k": 3},
        headers={"Authorization": "Bearer dev-token"},
    )
    assert s1.status_code == 200, s1.text
    body = s1.json()
    assert "suggestions" in body

    # Commit path should require lock
    s2 = client.post(
        f"/api/mcp/blueprints/partial/{pb_id}/suggest",
        json={"commit": True},
        headers={"Authorization": "Bearer dev-token"},
    )
    assert s2.status_code == 428

    # Fetch current lock via GET and try commit again
    get_pb = client.get(
        f"/api/mcp/blueprints/partial/{pb_id}",
        headers={"Authorization": "Bearer dev-token"},
    )
    assert get_pb.status_code == 200
    lock = get_pb.headers.get("X-Version-Lock")
    assert lock

    s3 = client.post(
        f"/api/mcp/blueprints/partial/{pb_id}/suggest",
        json={"commit": True},
        headers={"Authorization": "Bearer dev-token", "X-Version-Lock": lock},
    )
    assert s3.status_code == 200
