from __future__ import annotations

import os
from typing import Any, Dict

import httpx

BASE_URL = os.getenv("ICE_API_URL", "http://localhost:8000")
API_TOKEN = os.getenv("ICE_API_TOKEN", "dev-token")


def _auth() -> Dict[str, str]:
    return {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


def test_library_add_list_get_delete() -> None:
    url = f"{BASE_URL}/api/v1/library/assets"
    payload = {
        "label": "it_smoke",
        "content": "hello",
        "mime": "text/plain",
        "org_id": "demo_org",
        "user_id": "demo_user",
    }
    r = httpx.post(url, headers=_auth(), json=payload, timeout=10.0)
    assert r.status_code == 200, r.text
    data: Dict[str, Any] = r.json()
    assert data.get("ok") is True

    r2 = httpx.get(
        url,
        headers=_auth(),
        params={"org_id": "demo_org", "user_id": "demo_user", "limit": 5},
        timeout=10.0,
    )
    assert r2.status_code == 200, r2.text
    items = r2.json().get("items", [])
    assert any(i.get("key", "").endswith(":it_smoke") for i in items)

    r3 = httpx.get(
        f"{url}/it_smoke",
        headers=_auth(),
        params={"org_id": "demo_org", "user_id": "demo_user"},
        timeout=10.0,
    )
    assert r3.status_code == 200, r3.text
    one = r3.json()
    assert one.get("key", "").endswith(":it_smoke")

    r4 = httpx.delete(
        f"{url}/it_smoke",
        headers=_auth(),
        params={"org_id": "demo_org", "user_id": "demo_user"},
        timeout=10.0,
    )
    assert r4.status_code == 200, r4.text
