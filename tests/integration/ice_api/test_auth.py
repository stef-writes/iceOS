from __future__ import annotations

from fastapi.testclient import TestClient

from ice_api.main import app


def test_auth_rejects_without_flag(monkeypatch):
    """When ICE_ALLOW_DEV_TOKEN=0 and no DB token, requests must be rejected.

    This asserts the hardened auth default: dev-token is not accepted unless
    ICE_ALLOW_DEV_TOKEN=1.
    """
    # Ensure the environment disables dev token and no explicit API token is set
    monkeypatch.setenv("ICE_ALLOW_DEV_TOKEN", "0")
    monkeypatch.delenv("ICE_API_TOKEN", raising=False)
    client = TestClient(app)
    # Hit a protected route with a POST requiring auth
    resp = client.post(
        "/api/v1/blueprints/",
        headers={"Authorization": "Bearer dev-token", "X-Version-Lock": "__new__"},
        json={
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "x"},
            "nodes": [
                {
                    "id": "n1",
                    "type": "llm",
                    "model": "gpt-4o",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                }
            ],
        },
    )
    assert resp.status_code in (401, 403)
