from __future__ import annotations

from typing import Any, Dict

from starlette.testclient import TestClient

from ice_api.main import app


def _auth() -> Dict[str, str]:
    return {"Authorization": "Bearer dev-token", "Content-Type": "application/json"}


def test_library_add_list_get_delete() -> None:
    client = TestClient(app)
    url = "/api/v1/library/assets"
    payload = {
        "label": "it_smoke",
        "content": "hello",
        "mime": "text/plain",
        "org_id": "demo_org",
        "user_id": "demo_user",
    }
    r = client.post(url, headers=_auth(), json=payload)
    assert r.status_code == 200, r.text
    data: Dict[str, Any] = r.json()
    assert data.get("ok") is True

    # pagination: create a few
    for i in range(5):
        client.post(url, headers=_auth(), json={**payload, "label": f"p{i}"})

    r2 = client.get(
        url,
        headers=_auth(),
        params={"org_id": "demo_org", "user_id": "demo_user", "limit": 3},
    )
    assert r2.status_code == 200, r2.text
    items = r2.json().get("items", [])
    assert len(items) <= 3

    r3 = client.get(
        f"{url}/it_smoke",
        headers=_auth(),
        params={"org_id": "demo_org", "user_id": "demo_user"},
    )
    assert r3.status_code == 200, r3.text
    one = r3.json()
    assert one.get("key", "").endswith(":it_smoke")

    # large content should 413
    too_big = "x" * (1_000_001)
    r_big = client.post(
        url,
        headers=_auth(),
        json={**payload, "label": "too_big", "content": too_big},
    )
    assert r_big.status_code in {400, 413}

    r4 = client.delete(
        f"{url}/it_smoke",
        headers=_auth(),
        params={"org_id": "demo_org", "user_id": "demo_user"},
    )
    assert r4.status_code == 200, r4.text
