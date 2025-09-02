from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel, Field

from ice_api.dependencies import rate_limit
from ice_api.redis_client import get_redis
from ice_api.security import get_request_identity, require_auth


class DraftPayload(BaseModel):
    """Draft payload model.

    Attributes
    ----------
    data : dict[str, Any]
        Opaque draft data produced by the builder.
    version : int
        Optimistic concurrency version number (monotonic, starts at 1).

    Example
    -------
    >>> DraftPayload(data={"nodes": [], "metadata": {"draft_name": "wip"}}, version=1)
    """

    data: Dict[str, Any] = Field(default_factory=dict)
    version: int = 0


class DraftAck(BaseModel):
    """Acknowledgement of a draft operation."""

    key: str
    ok: bool = True
    version: int = 0


router = APIRouter(prefix="/api/v1/builder/drafts", tags=["builder", "drafts"])  # noqa: D401


def _draft_key(org_id: Optional[str], user_id: Optional[str], key: str) -> str:
    parts = ["builder:draft", org_id or "_", user_id or "_", key]
    return ":".join(parts)


@router.put(
    "/{key}",
    response_model=DraftAck,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def put_draft(
    request: Request,
    key: str = Path(..., description="Draft key identifier"),
    payload: DraftPayload = DraftPayload(),
) -> DraftAck:  # noqa: D401
    """Create or update a draft for the current identity.

    Uses optimistic concurrency via versioning:
    - If request has "If-Match: <version>", update only if current version matches.
    - Otherwise create-or-replace and bump version.
    """

    org_id, user_id = get_request_identity(request)

    redis = get_redis()
    redis_key = _draft_key(org_id, user_id, key)

    # Read current version
    raw_ver = await redis.hget(redis_key, "version")  # type: ignore[arg-type]
    current_version = int(raw_ver or 0)

    # If-Match header enforcement (optimistic concurrency)
    if_match = request.headers.get("If-Match")
    if if_match is not None:
        try:
            expected = int(if_match)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid If-Match header")
        if expected != current_version:
            raise HTTPException(status_code=409, detail="Draft version conflict")

    new_version = max(current_version, payload.version or 0) + 1

    ttl = int(os.getenv("ICE_BUILDER_DRAFT_TTL_SECONDS", "3600"))
    await redis.hset(
        redis_key,
        {
            "data": json.dumps(payload.data),
            "version": str(new_version),
        },
    )  # type: ignore[arg-type]
    if ttl > 0:
        try:
            from typing import Any as _Any

            _r_any: _Any = redis
            await _r_any.expire(redis_key, ttl)
        except Exception:
            pass
    return DraftAck(key=key, ok=True, version=new_version)


@router.get(
    "/{key}",
    response_model=DraftPayload,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def get_draft(
    request: Request, key: str = Path(..., description="Draft key identifier")
) -> DraftPayload:  # noqa: D401
    """Fetch a draft for the current identity.

    Returns current version and data. Raises 404 if not found.
    """

    org_id, user_id = get_request_identity(request)

    redis = get_redis()
    redis_key = _draft_key(org_id, user_id, key)
    raw = await redis.hget(redis_key, "data")  # type: ignore[arg-type]
    if raw is None:
        raise HTTPException(status_code=404, detail="draft not found")
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    raw_ver = await redis.hget(redis_key, "version")  # type: ignore[arg-type]
    version = int(raw_ver or 0)
    return DraftPayload(data=data, version=version)


@router.delete(
    "/{key}",
    response_model=DraftAck,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def delete_draft(
    request: Request, key: str = Path(..., description="Draft key identifier")
) -> DraftAck:  # noqa: D401
    """Delete a draft for the current identity (idempotent)."""

    org_id, user_id = get_request_identity(request)

    redis = get_redis()
    redis_key = _draft_key(org_id, user_id, key)
    await redis.hdel(redis_key, "data")  # type: ignore[arg-type]
    await redis.hdel(redis_key, "version")  # type: ignore[arg-type]
    return DraftAck(key=key, ok=True, version=0)
