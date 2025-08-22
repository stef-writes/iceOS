from __future__ import annotations

import asyncio
from typing import Optional

from ice_api.services.semantic_memory_repository import search_semantic
from ice_core.memory.embedders import get_embedder_from_env


async def probe(
    query: str, scope: Optional[str], org_id: Optional[str], limit: int = 5
) -> None:
    emb = get_embedder_from_env()
    qv = await emb.embed(query)
    rows = await search_semantic(scope=scope, query_vec=qv, limit=limit, org_id=org_id)
    print(f"probe result count (org={org_id}, scope={scope}):", len(rows))
    if rows:
        print("top keys:", [r.get("key") for r in rows[:5]])


def main() -> None:
    asyncio.run(probe("france capital", "kb", "o1", 5))
    asyncio.run(probe("raspberries", "kb", "orgZ", 5))
    asyncio.run(probe("cities colors", "kb", "orgL", 5))


if __name__ == "__main__":
    main()
