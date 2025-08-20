from __future__ import annotations

import anyio

from ice_api.services.vector_index_pg import PgVectorIndex


async def _run() -> bool:
    index = PgVectorIndex(embedding_dimension=1536)

    # Build simple 1536-D vectors where first components dominate
    def pad(vec):
        return vec + [0.0] * (1536 - len(vec))

    v1 = pad([1.0, 0.0])
    v2 = pad([0.0, 1.0])
    q = pad([0.9, 0.1])

    # Upsert
    await index.upsert("kb", "doc1", v1, model_version="test")
    await index.upsert("kb", "doc2", v2, model_version="test")

    # Query – pass org_id to match default storage behavior (_default_org)
    res = await index.query("kb", q, k=2, filter={"org_id": "_default_org"})
    assert res and res[0][0] == "doc1"
    return True


def test_pgvector_index_basic() -> None:
    assert anyio.run(_run)
