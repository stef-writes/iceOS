from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from ice_core.protocols.builder import DraftStoreProtocol


class HttpDraftStore(DraftStoreProtocol):
    """HTTP-backed DraftStore using API endpoints.

    Env vars:
      - ICE_API_URL (required)
      - ICE_API_TOKEN (required)
    """

    def validate(self) -> None:  # noqa: D401
        return None

    async def put(self, *, key: str, value: Dict[str, Any]) -> None:  # noqa: D401
        api_url = os.getenv("ICE_API_URL")
        token = os.getenv("ICE_API_TOKEN")
        if not api_url or not token:
            return
        url = f"{api_url.rstrip('/')}/api/v1/builder/drafts/{key}"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"data": value}
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.put(url, headers=headers, json=payload)
                r.raise_for_status()
        except Exception:
            return

    async def get(self, *, key: str) -> Optional[Dict[str, Any]]:  # noqa: D401
        api_url = os.getenv("ICE_API_URL")
        token = os.getenv("ICE_API_TOKEN")
        if not api_url or not token:
            return None
        url = f"{api_url.rstrip('/')}/api/v1/builder/drafts/{key}"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(url, headers=headers)
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                data = r.json() or {}
                if isinstance(data, dict) and isinstance(data.get("data"), dict):
                    from typing import cast

                    return cast(Dict[str, Any], data["data"])
                return None
        except Exception:
            return None


__all__ = ["HttpDraftStore"]
