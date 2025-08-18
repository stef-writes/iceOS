from __future__ import annotations

import anyio

from ice_api.services.vector_index_pg import PgVectorIndex


async def _run() -> bool:
    index = PgVectorIndex(embedding_dimension=8)

    # Two orthogonal-ish vectors; q closer to v1
    v1 = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    q = [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    # Upsert
    await index.upsert("kb", "doc1", v1, model_version="test")
    await index.upsert("kb", "doc2", v2, model_version="test")

    # Query
    res = await index.query("kb", q, k=2)
    assert res and res[0][0] == "doc1"
    return True


def test_pgvector_index_basic() -> None:
    assert anyio.run(_run)
