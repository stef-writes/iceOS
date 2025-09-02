from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx


async def list_library_assets_via_api(
    *,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    prefix: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Fetch library assets via the API (no direct DB access).

    Requires env vars:
      - ICE_API_URL
      - ICE_API_TOKEN
    """
    api_url = os.getenv("ICE_API_URL")
    token = os.getenv("ICE_API_TOKEN")
    if not api_url or not token:
        return []

    params: Dict[str, Any] = {"limit": limit}
    if org_id is not None:
        params["org_id"] = org_id
    if user_id is not None:
        params["user_id"] = user_id
    if prefix is not None:
        params["prefix"] = prefix

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{api_url.rstrip('/')}/api/v1/library/assets"
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json() or {}
            items = data.get("items") or []
            if not isinstance(items, list):
                return []
            return [
                {
                    "key": it.get("key"),
                    "scope": it.get("scope"),
                    "org_id": it.get("org_id"),
                    "user_id": it.get("user_id"),
                    "created_at": it.get("created_at"),
                }
                for it in items
                if isinstance(it, dict)
            ]
    except Exception:
        return []


__all__ = ["list_library_assets_via_api"]
