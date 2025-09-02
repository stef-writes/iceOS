from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx


async def list_recent_runs(limit: int = 20) -> List[Dict[str, Any]]:
    api_url = os.getenv("ICE_API_URL")
    token = os.getenv("ICE_API_TOKEN")
    if not api_url or not token:
        return []
    url = f"{api_url.rstrip('/')}/api/v1/executions/"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(url, headers=headers)
            r.raise_for_status()
            data = r.json() or {}
            items = data.get("executions") or []
            out: List[Dict[str, Any]] = []
            for it in items[: int(limit)]:
                if not isinstance(it, dict):
                    continue
                out.append(
                    {
                        "id": it.get("execution_id"),
                        "blueprint_id": it.get("blueprint_id"),
                        "status": it.get("status"),
                    }
                )
            return out
    except Exception:
        return []


__all__ = ["list_recent_runs"]
