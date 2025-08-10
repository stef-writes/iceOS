"""Mock marketplace endpoints for local testing.

Stores posted items in memory so front-end developers can fetch them without
hitting a real Facebook endpoint.
"""

from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, status

router = APIRouter(prefix="/api/v1/mock/marketplace", tags=["mock-marketplace"])

_STORE: List[dict[str, Any]] = []


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(item: dict[str, Any]) -> dict[str, Any]:  # noqa: D401
    _STORE.append(item)
    return {"status": "accepted", "index": len(_STORE) - 1}


@router.get("/items", response_model=List[dict[str, Any]])
async def list_items() -> List[dict[str, Any]]:  # noqa: D401
    return _STORE
