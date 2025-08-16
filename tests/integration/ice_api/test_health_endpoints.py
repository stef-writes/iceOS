from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def test_livez():
    resp = client.get("/livez")
    assert resp.status_code == 200
    assert resp.json()["status"] == "live"


def test_readyz():
    # READY_FLAG is set during lifespan startup in TestClient context
    resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json()["status"] in {"ready", "starting"}


def test_registry_health_includes_wasm_and_resource_defaults():
    resp = client.get("/api/v1/meta/registry/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "wasm" in data and isinstance(data["wasm"], dict)
    assert "enabled" in data["wasm"] and "arch" in data["wasm"]
    # Verify resource governance defaults are exposed
    assert "resource_governance" in data and isinstance(
        data["resource_governance"], dict
    )
    defaults = data["resource_governance"].get("defaults", {})
    assert set(["timeout_seconds", "memory_limit_mb", "cpu_limit_seconds"]).issubset(
        defaults.keys()
    )
