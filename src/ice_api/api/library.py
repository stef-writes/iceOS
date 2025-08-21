from __future__ import annotations

from hashlib import sha256
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text

from ice_api.db.database_session_async import get_session
from ice_api.security import require_auth
from ice_api.services.semantic_memory_repository import insert_semantic_entry

router = APIRouter(prefix="/api/v1/library", dependencies=[Depends(require_auth)])


MAX_CONTENT_BYTES = 1_000_000
ALLOWED_MIMES = {"text/plain", "text/markdown", "application/json"}


class LibraryAssetIn(BaseModel):
    label: str = Field(
        ..., description="Human label, unique per user", min_length=1, max_length=128
    )
    content: str = Field(..., description="Text content to store")
    mime: Optional[str] = Field(None, description="MIME type, e.g., text/plain")
    scope: str = Field("library", description="Logical scope, defaults to 'library'")
    org_id: Optional[str] = Field(None, description="Organization identifier")
    user_id: Optional[str] = Field(None, description="User identifier")


class LibraryAssetOut(BaseModel):
    key: str
    org_id: Optional[str]
    user_id: Optional[str]
    scope: str
    meta_json: Dict[str, Any]
    created_at: str


def _asset_key(user_id: str | None, label: str) -> str:
    uid = user_id or "_default_user"
    return f"asset:{uid}:{label}"


@router.post("/assets", response_model=Dict[str, Any])
async def add_asset(payload: LibraryAssetIn) -> Dict[str, Any]:
    """Create or update a user library asset using semantic memory storage.

    - Stores under scope 'library' by default
    - Key format: asset:{user_id}:{label}
    """

    raw = payload.content.encode("utf-8")
    if len(raw) > MAX_CONTENT_BYTES:
        raise HTTPException(status_code=413, detail="Content too large")
    if payload.mime and payload.mime not in ALLOWED_MIMES:
        raise HTTPException(status_code=415, detail="Unsupported MIME type")
    content_hash = sha256(raw).hexdigest()
    key = _asset_key(payload.user_id, payload.label)
    meta: Dict[str, Any] = {
        "content": payload.content,
        "mime": payload.mime or "text/plain",
        "category": "user_asset",
        "label": payload.label,
    }
    row_id = await insert_semantic_entry(
        scope=payload.scope,
        key=key,
        content_hash=content_hash,
        meta_json=meta,
        embedding_vec=None,
        org_id=payload.org_id,
        user_id=payload.user_id,
        model_version=None,
    )
    return {
        "ok": True,
        "row_id": row_id,
        "key": key,
        "scope": payload.scope,
        "org_id": payload.org_id,
        "user_id": payload.user_id,
    }


@router.get("/assets", response_model=Dict[str, Any])
async def list_assets(
    *,
    org_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    prefix: Optional[str] = Query(None, description="Filter by label prefix"),
    limit: int = Query(20, ge=1, le=200),
) -> Dict[str, Any]:
    prefix_key = _asset_key(user_id, (prefix or ""))
    async for session in get_session():
        where_parts = ["scope = :scope", "key LIKE :prefix"]
        params: Dict[str, Any] = {
            "scope": "library",
            "prefix": prefix_key + "%",
            "limit": limit,
        }
        if org_id is not None:
            where_parts.append("org_id = :org_id")
            params["org_id"] = org_id
        sql = f"""
            SELECT key, meta_json, org_id, user_id, scope, created_at
            FROM semantic_memory
            WHERE {' AND '.join(where_parts)}
            ORDER BY created_at DESC
            LIMIT :limit
        """
        stmt = text(sql).bindparams(
            bindparam("scope", type_=sa.String()),
            bindparam("prefix", type_=sa.String()),
            bindparam("limit", type_=sa.Integer()),
        )
        if org_id is not None:
            stmt = stmt.bindparams(bindparam("org_id", type_=sa.String()))
        rows = await session.execute(stmt, params)
        items: List[Dict[str, Any]] = []
        for r in rows.mappings():
            rec = dict(r)
            ca = rec.get("created_at")
            try:
                if ca is not None:
                    rec["created_at"] = ca.isoformat()
            except Exception:
                pass
            items.append(rec)
        return {"items": items}
    return {"items": []}


@router.get("/assets/{label}", response_model=LibraryAssetOut)
async def get_asset(
    label: str,
    *,
    org_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
) -> LibraryAssetOut:
    key = _asset_key(user_id, label)
    async for session in get_session():
        where_parts = ["scope = :scope", "key = :key"]
        params: Dict[str, Any] = {"scope": "library", "key": key}
        if org_id is not None:
            where_parts.append("org_id = :org_id")
            params["org_id"] = org_id
        sql = f"""
            SELECT key, meta_json, org_id, user_id, scope, created_at
            FROM semantic_memory
            WHERE {' AND '.join(where_parts)}
            ORDER BY created_at DESC
            LIMIT 1
        """
        stmt = text(sql).bindparams(
            bindparam("scope", type_=sa.String()),
            bindparam("key", type_=sa.String()),
        )
        if org_id is not None:
            stmt = stmt.bindparams(bindparam("org_id", type_=sa.String()))
        row = (await session.execute(stmt, params)).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found")
        rec = dict(row)
        ca = rec.get("created_at")
        try:
            if ca is not None:
                rec["created_at"] = ca.isoformat()
        except Exception:
            pass
        return LibraryAssetOut(**rec)
    raise HTTPException(status_code=500, detail="No DB session")


@router.delete("/assets/{label}", response_model=Dict[str, Any])
async def delete_asset(
    label: str,
    *,
    org_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    key = _asset_key(user_id, label)
    async for session in get_session():
        where_parts = ["key = :key", "scope = :scope"]
        params: Dict[str, Any] = {"key": key, "scope": "library"}
        if org_id is not None:
            where_parts.append("org_id = :org_id")
            params["org_id"] = org_id
        sql = f"DELETE FROM semantic_memory WHERE {' AND '.join(where_parts)}"
        stmt = text(sql).bindparams(
            bindparam("key", type_=sa.String()), bindparam("scope", type_=sa.String())
        )
        if org_id is not None:
            stmt = stmt.bindparams(bindparam("org_id", type_=sa.String()))
        await session.execute(stmt, params)
        await session.commit()
        return {"ok": True, "key": key}
    raise HTTPException(status_code=500, detail="No DB session")
