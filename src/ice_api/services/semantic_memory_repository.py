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
            INSERT INTO semantic_memory (
                scope, key, content_hash, model_version, meta_json, embedding, org_id, user_id
            )
            VALUES (
                :scope, :key, :content_hash, :model_version, :meta_json, (:embedding)::vector, :org_id, :user_id
            )
            ON CONFLICT (org_id, content_hash) DO UPDATE SET
                key = EXCLUDED.key,
                scope = EXCLUDED.scope,
                model_version = EXCLUDED.model_version,
                meta_json = COALESCE(semantic_memory.meta_json::jsonb, '{}'::jsonb) || EXCLUDED.meta_json::jsonb,
                embedding = EXCLUDED.embedding
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
            "org_id": org_id or "_default_org",
            "user_id": user_id or "_default_user",
        },
    )
    row = result.first()
    await session.commit()
    try:
        # Diagnostics: count rows for org/scope
        cnt_res = await session.execute(
            text(
                "SELECT COUNT(*) FROM semantic_memory WHERE org_id = :org AND scope = :scope"
            ),
            {"org": org_id or "_default_org", "scope": scope},
        )
        cnt = int(cnt_res.scalar() or 0)
        logger.debug(
            "semantic_memory.insert_post_count",
            extra={"org_id": org_id or "_default_org", "scope": scope, "count": cnt},
        )
    except Exception:
        pass
    return int(row[0]) if row else None


async def search_semantic(
    *,
    scope: str | None,
    query_vec: list[float],
    limit: int = 10,
    org_id: str | None = None,
    category: str | None = None,
    tags: List[str] | None = None,
) -> List[Dict[str, Any]]:
    qvec_literal = "[" + ",".join(f"{x:.6f}" for x in query_vec) + "]"
    rows_out: List[Dict[str, Any]] = []
    async for session in get_session():
        logger.info(
            "semantic_memory.search",
            extra={"scope": scope, "org_id": org_id, "limit": limit},
        )
        # Build SQL conditionally to avoid NULL-typed parameter edge cases
        where_clauses = [
            "(:scope IS NULL OR scope = :scope)",
            "(:org_id IS NULL OR org_id = :org_id)",
            "embedding IS NOT NULL",
        ]
        params: Dict[str, Any] = {
            "scope": scope,
            "org_id": org_id,
            "qvec": qvec_literal,
            "limit": limit,
        }
        if category is not None:
            where_clauses.append("meta_json->> 'category' = :category")
            params["category"] = category
        if tags:
            where_clauses.append("CAST(meta_json AS JSONB) @> (:tags_filter)::JSONB")
            params["tags_filter"] = {"tags": tags}

        sql = f"""
            SELECT id, scope, key, content_hash, model_version, meta_json, created_at,
                   1 - (embedding <=> (:qvec)::vector) AS cosine_similarity
            FROM semantic_memory
            WHERE {' AND '.join(where_clauses)}
            ORDER BY embedding <-> (:qvec)::vector
            LIMIT :limit
        """
        stmt = text(sql).bindparams(
            bindparam("qvec", type_=sa.Text()),
            bindparam("scope", type_=sa.String()),
            bindparam("org_id", type_=sa.String()),
            bindparam("limit", type_=sa.Integer()),
        )
        if category is not None:
            stmt = stmt.bindparams(bindparam("category", type_=sa.String()))
        if tags:
            stmt = stmt.bindparams(bindparam("tags_filter", type_=JSONB))

        rows = await session.execute(stmt, params)
        fetched: list[Dict[str, Any]] = []
        for r in rows.mappings():
            row_dict = dict(r)
            created_at_val = row_dict.get("created_at")
            if created_at_val is not None and hasattr(created_at_val, "isoformat"):
                row_dict["created_at"] = created_at_val.isoformat()
            fetched.append(row_dict)
        rows_out.extend(fetched)
        try:
            logger.debug(
                "semantic_memory.search_results",
                extra={
                    "scope": scope,
                    "org_id": org_id,
                    "returned": len(fetched),
                },
            )
        except Exception:
            pass
    return rows_out
