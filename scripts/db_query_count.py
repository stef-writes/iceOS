from __future__ import annotations

import asyncio
from typing import Optional

from sqlalchemy import text


async def _run(scope: Optional[str], org_id: Optional[str]) -> None:
    from ice_api.db.database_session_async import get_engine

    eng = get_engine()
    assert eng is not None
    async with eng.connect() as conn:  # type: ignore[call-arg]
        res = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM semantic_memory
                WHERE (:scope IS NULL OR scope = :scope)
                  AND (:org_id IS NULL OR org_id = :org_id)
                  AND embedding IS NOT NULL
                """
            ),
            {"scope": scope, "org_id": org_id},
        )
        print(f"count(scope={scope}, org={org_id}):", res.scalar())


def main() -> None:
    asyncio.run(_run("kb", "o1"))
    asyncio.run(_run("kb", "orgZ"))
    asyncio.run(_run("kb", "orgL"))
    asyncio.run(_run("kb", None))


if __name__ == "__main__":
    main()
