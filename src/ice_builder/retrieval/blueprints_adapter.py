from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx


async def list_blueprints(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch blueprint ids via the API index endpoint (no DB imports)."""
    api_url = os.getenv("ICE_API_URL")
    token = os.getenv("ICE_API_TOKEN")
    if not api_url or not token:
        return []
    url = f"{api_url.rstrip('/')}/api/v1/library/assets/index"
    params = {"kind": "blueprint", "limit": int(limit)}
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json() or {}
            items = data.get("items") or []
            result: List[Dict[str, Any]] = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                if it.get("kind") == "blueprint":
                    result.append({"id": it.get("name"), "schema_version": None})
            return result
    except Exception:
        return []


__all__ = ["list_blueprints"]
