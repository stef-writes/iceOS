from __future__ import annotations

import datetime as _dt
import hashlib
import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ice_api.db.database_session_async import session_scope
from ice_api.db.orm_models_core import TokenRecord
from ice_api.security import require_auth

router = APIRouter(
    prefix="/api/v1/tokens", tags=["tokens"], dependencies=[Depends(require_auth)]
)


class TokenIssueRequest(BaseModel):
    org_id: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    scopes: List[str] = Field(default_factory=list)
    ttl_days: Optional[int] = Field(default=None, ge=1, le=3650)
    expires_at: Optional[_dt.datetime] = Field(default=None)


class TokenIssueResponse(BaseModel):
    token: str
    token_hash: str
    org_id: Optional[str]
    project_id: Optional[str]
    user_id: Optional[str]
    scopes: List[str]
    expires_at: Optional[str]


@router.post(
    "/", response_model=TokenIssueResponse, status_code=status.HTTP_201_CREATED
)
async def issue_token(req: TokenIssueRequest) -> TokenIssueResponse:  # noqa: D401
    """Issue a new bearer token and persist its hash.

    The raw token is returned once; only the hash is stored server-side.
    """
    raw = secrets.token_urlsafe(32)
    th = hashlib.sha256(raw.encode()).hexdigest()

    expires_at: Optional[_dt.datetime] = None
    if req.expires_at is not None:
        expires_at = req.expires_at
    elif req.ttl_days is not None:
        expires_at = _dt.datetime.utcnow().replace(
            tzinfo=_dt.timezone.utc
        ) + _dt.timedelta(days=int(req.ttl_days))

    async with session_scope() as session:
        rec = TokenRecord(
            token_hash=th,
            org_id=req.org_id,
            project_id=req.project_id,
            user_id=req.user_id,
            scopes=list(req.scopes) if req.scopes else None,
            expires_at=expires_at,
            revoked=False,
        )
        session.add(rec)
        await session.commit()

    return TokenIssueResponse(
        token=raw,
        token_hash=th,
        org_id=req.org_id,
        project_id=req.project_id,
        user_id=req.user_id,
        scopes=list(req.scopes),
        expires_at=(
            expires_at.isoformat() if isinstance(expires_at, _dt.datetime) else None
        ),
    )


class TokenListItem(BaseModel):
    token_hash: str
    org_id: Optional[str]
    project_id: Optional[str]
    user_id: Optional[str]
    scopes: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    revoked: bool


class TokenListResponse(BaseModel):
    items: List[TokenListItem]


@router.get("/", response_model=TokenListResponse)
async def list_tokens(
    org_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> TokenListResponse:  # noqa: D401
    async with session_scope() as session:
        from sqlalchemy import select

        stmt = select(TokenRecord).limit(limit)
        if org_id is not None:
            stmt = stmt.where(TokenRecord.org_id == org_id)
        if project_id is not None:
            stmt = stmt.where(TokenRecord.project_id == project_id)
        if user_id is not None:
            stmt = stmt.where(TokenRecord.user_id == user_id)
        rows = (await session.execute(stmt)).scalars().all()
        items: List[TokenListItem] = []
        for r in rows:
            created_at_val = getattr(r, "created_at", None)
            expires_at_val = getattr(r, "expires_at", None)
            items.append(
                TokenListItem(
                    token_hash=r.token_hash,
                    org_id=r.org_id,
                    project_id=r.project_id,
                    user_id=r.user_id,
                    scopes=list(r.scopes or []),
                    created_at=(
                        created_at_val.isoformat()
                        if isinstance(created_at_val, _dt.datetime)
                        else None
                    ),
                    expires_at=(
                        expires_at_val.isoformat()
                        if isinstance(expires_at_val, _dt.datetime)
                        else None
                    ),
                    revoked=bool(r.revoked),
                )
            )
        return TokenListResponse(items=items)

    return TokenListResponse(items=[])


class TokenRevokeRequest(BaseModel):
    token_hash: str


@router.post("/revoke", response_model=Dict[str, Any])
async def revoke_token(req: TokenRevokeRequest) -> Dict[str, Any]:  # noqa: D401
    async with session_scope() as session:
        rec = await session.get(TokenRecord, req.token_hash)
        if rec is None:
            raise HTTPException(status_code=404, detail="Token not found")
        rec.revoked = True
        await session.commit()
        return {"ok": True}
    raise HTTPException(status_code=500, detail="No DB session")


@router.delete("/{token_hash}", response_model=Dict[str, Any])
async def delete_token(token_hash: str) -> Dict[str, Any]:  # noqa: D401
    async with session_scope() as session:
        rec = await session.get(TokenRecord, token_hash)
        if rec is None:
            raise HTTPException(status_code=404, detail="Token not found")
        await session.delete(rec)
        await session.commit()
        return {"ok": True}
    raise HTTPException(status_code=500, detail="No DB session")
