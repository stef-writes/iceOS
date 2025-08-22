from __future__ import annotations

import asyncio

from sqlalchemy import text


async def _run() -> None:
    from ice_api.db.database_session_async import get_engine

    engine = get_engine()
    if engine is None:
        print("No engine; DATABASE_URL not set")
        return
    async with engine.connect() as conn:  # type: ignore[call-arg]
        r = await conn.execute(text("select count(*) from semantic_memory"))
        print("total:", r.scalar())
        r = await conn.execute(
            text(
                "select org_id, scope, count(*) c from semantic_memory group by org_id, scope order by c desc"
            )
        )
        rows = [tuple(row) for row in r]
        print("by_org_scope:", rows)
        r = await conn.execute(
            text(
                "select id, org_id, scope, key, (embedding is not null) as has_emb from semantic_memory order by id desc limit 10"
            )
        )
        print("sample:", [tuple(row) for row in r])


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
