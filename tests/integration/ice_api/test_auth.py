from __future__ import annotations

from fastapi.testclient import TestClient

from ice_api.main import app


def test_auth_rejects_without_flag(monkeypatch):
    """When ICE_ALLOW_DEV_TOKEN=0 and no DB token, requests must be rejected.

    This asserts the hardened auth default: dev-token is not accepted unless
    ICE_ALLOW_DEV_TOKEN=1.
    """
    # Ensure the environment disables dev token
    monkeypatch.setenv("ICE_ALLOW_DEV_TOKEN", "0")
    # No ICE_API_TOKEN provided in env here
    client = TestClient(app)
    resp = client.get(
        "/api/v1/meta/version", headers={"Authorization": "Bearer dev-token"}
    )
    assert resp.status_code in (401, 403)
