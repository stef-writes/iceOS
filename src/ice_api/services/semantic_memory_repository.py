from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ice_api.db.database_session_async import get_session


async def insert_semantic_entry(
    *,
    scope: str,
    key: str,
    content_hash: str,
    meta_json: Dict[str, Any] | None,
    embedding_vec: list[float] | None,
    org_id: str | None = None,
    user_id: str | None = None,
    model_version: str | None = None,
) -> Optional[int]:
    """Insert a semantic memory record.

    Returns the new row id or None if it already existed.
    """
    async for session in get_session():
        return await _insert_with_session(
            session=session,
            scope=scope,
            key=key,
            content_hash=content_hash,
            meta_json=meta_json or {},
            embedding_vec=embedding_vec,
            org_id=org_id,
            user_id=user_id,
            model_version=model_version,
        )
    return None


async def _insert_with_session(
    *,
    session: AsyncSession,
    scope: str,
    key: str,
    content_hash: str,
    meta_json: Dict[str, Any],
    embedding_vec: list[float] | None,
    org_id: str | None,
    user_id: str | None,
    model_version: str | None,
) -> Optional[int]:
    qvec_literal = (
        "[" + ",".join(f"{x:.6f}" for x in embedding_vec) + "]"
        if embedding_vec
        else None
    )
    result = await session.execute(
        text(
            """
            INSERT INTO semantic_memory (scope, key, content_hash, model_version, meta_json, embedding, org_id, user_id)
            VALUES (:scope, :key, :content_hash, :model_version, :meta_json, :embedding::vector, :org_id, :user_id)
            ON CONFLICT (org_id, content_hash) DO NOTHING
            RETURNING id
            """
        ),
        {
            "scope": scope,
            "key": key,
            "content_hash": content_hash,
            "model_version": model_version,
            "meta_json": meta_json,
            "embedding": qvec_literal,
            "org_id": org_id,
            "user_id": user_id,
        },
    )
    row = result.first()
    await session.commit()
    return int(row[0]) if row else None


async def search_semantic(
    *,
    scope: str | None,
    query_vec: list[float],
    limit: int = 10,
    org_id: str | None = None,
) -> List[Dict[str, Any]]:
    qvec_literal = "[" + ",".join(f"{x:.6f}" for x in query_vec) + "]"
    rows_out: List[Dict[str, Any]] = []
    async for session in get_session():
        rows = await session.execute(
            text(
                """
                SELECT id, scope, key, content_hash, model_version, meta_json, created_at,
                       1 - (embedding <=> :qvec::vector) AS cosine_similarity
                FROM semantic_memory
                WHERE (:scope IS NULL OR scope = :scope)
                  AND (:org_id IS NULL OR org_id = :org_id)
                  AND embedding IS NOT NULL
                ORDER BY embedding <-> :qvec::vector
                LIMIT :limit
                """
            ),
            {"scope": scope, "qvec": qvec_literal, "limit": limit, "org_id": org_id},
        )
        for r in rows.mappings():
            rows_out.append(dict(r))
    return rows_out
