from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel, Field

from ice_api.dependencies import rate_limit
from ice_api.redis_client import get_redis
from ice_api.security import get_request_identity, require_auth


class SessionPayload(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)


class SessionAck(BaseModel):
    session_id: str
    ok: bool = True


router = APIRouter(
    prefix="/api/v1/builder/sessions",
    tags=["builder", "sessions"],
    dependencies=[Depends(require_auth)],
)


def _sess_key(org_id: Optional[str], user_id: Optional[str], session_id: str) -> str:
    return ":".join(["builder:session", org_id or "_", user_id or "_", session_id])


def _identity_from_request(request: Request) -> tuple[Optional[str], Optional[str]]:
    try:
        org_id, user_id = get_request_identity(request)
        return org_id, user_id
    except Exception:
        return None, None


@router.put(
    "/{session_id}",
    response_model=SessionAck,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit)],
)
async def put_session(
    request: Request,
    session_id: str = Path(...),
    payload: SessionPayload = SessionPayload(),
) -> SessionAck:
    org_id, user_id = _identity_from_request(request)
    redis = get_redis()
    key = _sess_key(org_id, user_id, session_id)
    await redis.hset(key, {"data": json.dumps(payload.data)})  # type: ignore[arg-type]
    return SessionAck(session_id=session_id, ok=True)


@router.get(
    "/{session_id}",
    response_model=SessionPayload,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit)],
)
async def get_session(request: Request, session_id: str = Path(...)) -> SessionPayload:
    org_id, user_id = _identity_from_request(request)
    redis = get_redis()
    key = _sess_key(org_id, user_id, session_id)
    raw = await redis.hget(key, "data")  # type: ignore[arg-type]
    if raw is None:
        raise HTTPException(status_code=404, detail="session not found")
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    return SessionPayload(data=data)


@router.delete(
    "/{session_id}",
    response_model=SessionAck,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit)],
)
async def delete_session(request: Request, session_id: str = Path(...)) -> SessionAck:
    org_id, user_id = _identity_from_request(request)
    redis = get_redis()
    key = _sess_key(org_id, user_id, session_id)
    await redis.hdel(key, "data")  # type: ignore[arg-type]
    return SessionAck(session_id=session_id, ok=True)
