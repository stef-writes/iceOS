from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta

from sqlalchemy import text

from ice_api.db.database_session_async import get_session


async def run_decay(dry_run: bool = False) -> dict[str, int]:
    ttl_days = int(os.getenv("SEMANTIC_TTL_DAYS", "90"))
    cutoff = datetime.utcnow() - timedelta(days=ttl_days)
    # keep summaries regardless
    deleted = 0
    async for session in get_session():
        if dry_run:
            res = await session.execute(
                text(
                    """
                    SELECT count(*) FROM semantic_memory
                    WHERE created_at < :cutoff AND key NOT LIKE 'summary:%'
                    """
                ),
                {"cutoff": cutoff},
            )
            deleted = int(res.scalar() or 0)
        else:
            res = await session.execute(
                text(
                    """
                    DELETE FROM semantic_memory
                    WHERE created_at < :cutoff AND key NOT LIKE 'summary:%'
                    """
                ),
                {"cutoff": cutoff},
            )
            deleted = res.rowcount or 0
            await session.commit()
    return {"deleted": deleted}


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Semantic memory decay maintenance")
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()
    out = asyncio.run(run_decay(dry_run=ns.dry_run))
    print(json.dumps(out))
