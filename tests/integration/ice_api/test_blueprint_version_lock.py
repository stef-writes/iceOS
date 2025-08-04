import json

from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def _create_sample_blueprint():
    payload = {
        "name": "hello",
        "nodes": [{"id": "n1", "type": "tool"}],
        "metadata": {}
    }
    res = client.post(
        "/api/v1/blueprints/",
        json=payload,
        headers={
            "Authorization": "Bearer demo-token",
            "X-Version-Lock": "__new__",
        },
    )
    assert res.status_code == 201
    data = res.json()
    return data["id"], data["version_lock"]


def test_create_requires_header():
    payload = {"name": "b", "nodes": [], "metadata": {}}
    res = client.post("/api/v1/blueprints/", json=payload, headers={"Authorization": "Bearer demo-token"})
    assert res.status_code == 428


def test_create_conflict_header():
    payload = {"name": "b", "nodes": [], "metadata": {}}
    res = client.post(
        "/api/v1/blueprints/",
        json=payload,
        headers={"Authorization": "Bearer demo-token", "X-Version-Lock": "wrong"},
    )
    assert res.status_code == 409


def test_patch_happy_path():
    blueprint_id, lock = _create_sample_blueprint()

    patch_payload = {"nodes": [{"id": "n1", "type": "__delete__"}]}
    res = client.patch(
        f"/api/v1/blueprints/{blueprint_id}",
        json=patch_payload,
        headers={"X-Version-Lock": lock, "Authorization": "Bearer demo-token"},
    )
    assert res.status_code == 200
    assert res.json()["id"] == blueprint_id


def test_patch_conflict():
    blueprint_id, lock = _create_sample_blueprint()

    # first patch to change state so lock becomes stale
    client.patch(
        f"/api/v1/blueprints/{blueprint_id}",
        json={"nodes": [{"id": "n1", "type": "__delete__"}]},
        headers={"X-Version-Lock": lock, "Authorization": "Bearer demo-token"},
    )

    # second patch with old lock should fail
    res = client.patch(
        f"/api/v1/blueprints/{blueprint_id}",
        json={"nodes": []},
        headers={"X-Version-Lock": lock, "Authorization": "Bearer demo-token"},
    )
    assert res.status_code == 409
