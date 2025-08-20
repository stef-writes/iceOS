from __future__ import annotations

import asyncio

from sqlalchemy import text


async def main() -> None:
    from ice_api.db.database_session_async import get_engine

    eng = get_engine()
    assert eng is not None
    async with eng.connect() as conn:  # type: ignore[call-arg]
        r = await conn.execute(
            text("SELECT extversion FROM pg_extension WHERE extname='vector'")
        )
        print("pgvector extversion:", r.scalar())
        r = await conn.execute(
            text("""
            SELECT attname, atttypid::regtype
            FROM pg_attribute
            WHERE attrelid='semantic_memory'::regclass AND attname='embedding'
        """)
        )
        print("embedding column:", [tuple(x) for x in r])
        # Try operator without params
        r = await conn.execute(
            text("""
            SELECT id, key, 1 - (embedding <=> embedding) AS cosine
            FROM semantic_memory
            WHERE embedding IS NOT NULL
            ORDER BY embedding <-> embedding
            LIMIT 5
        """)
        )
        rows = [tuple(x) for x in r]
        print("self-distance rows:", rows)


if __name__ == "__main__":
    asyncio.run(main())
