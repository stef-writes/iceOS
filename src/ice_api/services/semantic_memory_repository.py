from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from ice_api.db.database_session_async import get_session

logger = logging.getLogger(__name__)


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
        logger.info(
            "semantic_memory.insert",
            extra={
                "scope": scope,
                "org_id": org_id,
                "user_id": user_id,
                "model_version": model_version,
            },
        )
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
    # Ensure embedding matches pgvector column dimension (1536). Adjust only by error to avoid silent drift.
    if embedding_vec is not None and len(embedding_vec) != 1536:
        raise ValueError(
            f"Embedding dimension mismatch: expected 1536, got {len(embedding_vec)}"
        )
    qvec_literal = (
        "[" + ",".join(f"{x:.6f}" for x in embedding_vec) + "]"
        if embedding_vec
        else None
    )
    stmt = (
        text(
            """
            INSERT INTO semantic_memory (scope, key, content_hash, model_version, meta_json, embedding, org_id, user_id)
            VALUES (:scope, :key, :content_hash, :model_version, :meta_json, (:embedding)::vector, :org_id, :user_id)
            ON CONFLICT (org_id, content_hash) DO NOTHING
            RETURNING id
            """
        )
        # Ensure JSON param is adapted correctly by asyncpg
        .bindparams(bindparam("meta_json", type_=JSONB))
    )
    result = await session.execute(
        stmt,
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
        logger.info(
            "semantic_memory.search",
            extra={"scope": scope, "org_id": org_id, "limit": limit},
        )
        stmt = text(
            """
                SELECT id, scope, key, content_hash, model_version, meta_json, created_at,
                       1 - (embedding <=> (:qvec)::vector) AS cosine_similarity
                FROM semantic_memory
                WHERE (:scope IS NULL OR scope = :scope)
                  AND (:org_id IS NULL OR org_id = :org_id)
                  AND embedding IS NOT NULL
                ORDER BY embedding <-> (:qvec)::vector
                LIMIT :limit
                """
        ).bindparams(
            bindparam("qvec", type_=sa.Text()),
            bindparam("scope", type_=sa.String()),
            bindparam("org_id", type_=sa.String()),
            bindparam("limit", type_=sa.Integer()),
        )
        rows = await session.execute(
            stmt,
            {"scope": scope, "qvec": qvec_literal, "limit": limit, "org_id": org_id},
        )
        for r in rows.mappings():
            row_dict = dict(r)
            created_at_val = row_dict.get("created_at")
            if created_at_val is not None and hasattr(created_at_val, "isoformat"):
                row_dict["created_at"] = created_at_val.isoformat()
            rows_out.append(row_dict)
    return rows_out
