from __future__ import annotations

import asyncio

import sqlalchemy as sa
from sqlalchemy import bindparam, text


async def run_one(
    query: str, scope: str | None, org_id: str | None, limit: int
) -> None:
    from ice_api.db.database_session_async import get_engine
    from ice_core.memory.embedders import get_embedder_from_env

    emb = get_embedder_from_env()
    vec = await emb.embed(query)
    qvec_literal = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

    eng = get_engine()
    assert eng is not None
    async with eng.connect() as conn:  # type: ignore[call-arg]
        stmt = text(
            """
            SELECT id, scope, key, 1 - (embedding <=> (:qvec)::vector) AS cosine
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
        res = await conn.execute(
            stmt,
            {"qvec": qvec_literal, "scope": scope, "org_id": org_id, "limit": limit},
        )
        rows = [dict(r._mapping) for r in res]
        print(
            f"sql rows for org={org_id} scope={scope}:",
            len(rows),
            [r.get("key") for r in rows],
        )


async def main() -> None:
    await run_one("france capital", "kb", "o1", 5)
    await run_one("raspberries", "kb", "orgZ", 5)
    await run_one("cities colors", "kb", "orgL", 5)


if __name__ == "__main__":
    asyncio.run(main())
