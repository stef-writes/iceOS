from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def _create_sample_blueprint():
    """Helper that creates a minimal blueprint and returns (id, version_lock)."""
    payload = {
        "name": "hello",
        "nodes": [{"id": "n1", "type": "tool"}],
        "metadata": {},
    }
    res = client.post(
        "/api/v1/blueprints/",
        json=payload,
        headers={"Authorization": "Bearer demo-token", "X-Version-Lock": "__new__"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    return data["id"], data["version_lock"]


# ---------------------------------------------------------------------------
# DELETE ---------------------------------------------------------------------
# ---------------------------------------------------------------------------


def test_delete_blueprint_happy_path():
    blueprint_id, lock = _create_sample_blueprint()

    res = client.delete(
        f"/api/v1/blueprints/{blueprint_id}",
        headers={"Authorization": "Bearer demo-token", "X-Version-Lock": lock},
    )
    assert res.status_code == 204

    # Getting it afterwards should 404
    res2 = client.get(
        f"/api/v1/blueprints/{blueprint_id}",
        headers={"Authorization": "Bearer demo-token"},
    )
    assert res2.status_code == 404


def test_delete_missing_header():
    blueprint_id, _ = _create_sample_blueprint()
    res = client.delete(
        f"/api/v1/blueprints/{blueprint_id}",
        headers={"Authorization": "Bearer demo-token"},
    )
    assert res.status_code == 428


def test_delete_conflict():
    blueprint_id, lock = _create_sample_blueprint()

    # Patch to change version lock
    client.patch(
        f"/api/v1/blueprints/{blueprint_id}",
        json={"nodes": [{"id": "n2", "type": "tool"}]},
        headers={"Authorization": "Bearer demo-token", "X-Version-Lock": lock},
    )

    res = client.delete(
        f"/api/v1/blueprints/{blueprint_id}",
        headers={"Authorization": "Bearer demo-token", "X-Version-Lock": lock},
    )
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# PUT ------------------------------------------------------------------------
# ---------------------------------------------------------------------------


def test_put_blueprint_happy_path():
    blueprint_id, lock = _create_sample_blueprint()
    new_payload = {
        "name": "updated",
        "nodes": [{"id": "n2", "type": "tool"}],
        "metadata": {"v": 2},
    }
    res = client.put(
        f"/api/v1/blueprints/{blueprint_id}",
        json=new_payload,
        headers={"Authorization": "Bearer demo-token", "X-Version-Lock": lock},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == blueprint_id
    assert body["version_lock"] != lock


def test_put_missing_header():
    blueprint_id, _ = _create_sample_blueprint()
    res = client.put(
        f"/api/v1/blueprints/{blueprint_id}",
        json={"name": "x", "nodes": [], "metadata": {}},
        headers={"Authorization": "Bearer demo-token"},
    )
    assert res.status_code == 428


def test_put_conflict():
    blueprint_id, lock = _create_sample_blueprint()
    # change blueprint so lock stale
    client.patch(
        f"/api/v1/blueprints/{blueprint_id}",
        json={"nodes": [{"id": "n3", "type": "tool"}]},
        headers={"Authorization": "Bearer demo-token", "X-Version-Lock": lock},
    )
    res = client.put(
        f"/api/v1/blueprints/{blueprint_id}",
        json={"name": "x", "nodes": [], "metadata": {}},
        headers={"Authorization": "Bearer demo-token", "X-Version-Lock": lock},
    )
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# CLONE ----------------------------------------------------------------------
# ---------------------------------------------------------------------------


def test_clone_blueprint():
    blueprint_id, _ = _create_sample_blueprint()

    res = client.post(
        f"/api/v1/blueprints/{blueprint_id}/clone",
        headers={"Authorization": "Bearer demo-token"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["id"] != blueprint_id
    assert body["version_lock"]
