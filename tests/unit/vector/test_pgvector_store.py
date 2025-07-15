from __future__ import annotations

"""Integration tests for PgVectorStore adapter using a real Postgres + pgvector.

The test spins up a temporary Postgres container (via *testcontainers*) that
includes the pgvector extension, applies the migration SQL script, and then
verifies that ``PgVectorStore.upsert`` and ``query`` round-trip correctly.
"""

import asyncio
import pathlib
import random
import uuid
from typing import AsyncGenerator, List

import pytest

# Skip entire module if testcontainers/asyncpg are absent --------------------
pytest.importorskip("testcontainers.postgres")
testcontainers_postgres = pytest.importorskip("testcontainers.postgres")  # noqa: F841

asyncpg = pytest.importorskip("asyncpg")  # type: ignore  # noqa: F841

# Only import after ensuring availability to avoid early ImportError --------
from testcontainers.postgres import PostgresContainer  # type: ignore  # noqa: E402

from ice_sdk.providers.vector.pgvector import PgVectorStore  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------

_EMBED_DIM = 1536


def _random_vector(dim: int = _EMBED_DIM) -> List[float]:  # noqa: D401 – helper
    return [random.random() for _ in range(dim)]


# ---------------------------------------------------------------------------
# Fixtures ------------------------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def supabase_pg_container() -> AsyncGenerator[dict[str, str], None]:  # noqa: D401
    """Spin up Postgres 15 + pgvector container and apply migration script."""

    # Ankane/pgvector image already has pgvector extension pre-installed.
    with PostgresContainer("ankane/pgvector:latest") as pg:
        conn_url = pg.get_connection_url()

        # Apply migration SQL -------------------------------------------------
        migration_sql = pathlib.Path("scripts/migrate_to_supabase.sql").read_text()
        # Use sync connection for bootstrap to avoid event-loop mismatch.
        import psycopg2  # type: ignore

        with psycopg2.connect(conn_url) as conn:  # pragma: no cover – test env
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(migration_sql)

        yield {"sql_url": conn_url}
    # Container auto-stops here


@pytest.fixture()
async def store(monkeypatch, supabase_pg_container):  # noqa: D401 – fixture
    """Return PgVectorStore patched with a fake SupabaseClient that talks SQL."""

    sql_url = supabase_pg_container["sql_url"]

    # ------------------------------------------------------------------
    # Build asyncpg connection shared by stub client -------------------
    # ------------------------------------------------------------------
    conn = await asyncpg.connect(sql_url)

    class _Resp:  # noqa: D401 – simple container
        def __init__(self, data):
            self.data = data
            self.error = None

    class _StubClient:  # noqa: D401 – mimics supabase-py subset
        def __init__(self, _conn):
            self._conn = _conn
            self._table_name: str | None = None
            self._payload: dict | None = None

        # ---------------------- table / upsert -------------------------
        def table(self, name: str):  # noqa: D401 – chainable
            self._table_name = name
            return self

        def upsert(self, payload):  # noqa: D401 – chainable
            self._payload = payload
            return self

        async def _execute_upsert(self):
            p = self._payload or {}
            # Convert embedding list -> vector literal '[0.1,0.2]' -------------
            emb_literal = "[" + ",".join(map(str, p["embedding"])) + "]"
            row = await self._conn.fetchrow(
                """
                insert into documents (project_id, content, embedding, embedding_model)
                values ($1::uuid, $2, $3::vector, $4)
                returning id
                """,
                p["project_id"],
                p["content"],
                emb_literal,
                p["embedding_model"],
            )
            return _Resp([{"id": str(row["id"])}])

        # ---------------------- rpc -----------------------------------
        def rpc(self, func: str, payload):  # noqa: D401 – chainable
            self._rpc_name = func
            self._payload = payload
            return self

        async def _execute_rpc(self):
            p = self._payload or {}
            emb_literal = "[" + ",".join(map(str, p["query_embedding"])) + "]"
            rows = await self._conn.fetch(
                """
                select id, content, (embedding <=> $1::vector) as distance
                  from documents
                 where project_id = $2::uuid
              order by distance
                 limit $3::int
                """,
                emb_literal,
                p["project_id"],
                p["match_count"],
            )
            data = [
                {
                    "id": str(r["id"]),
                    "content": r["content"],
                    "distance": float(r["distance"]),
                }
                for r in rows
            ]
            return _Resp(data)

        # ---------------------- adapter --------------------------------
        def execute(self):  # noqa: D401 – supabase-py sync interface stub
            # Determine whether this is an upsert or rpc based on attributes.
            if self._table_name:
                return asyncio.get_event_loop().run_until_complete(
                    self._execute_upsert()
                )
            else:
                return asyncio.get_event_loop().run_until_complete(self._execute_rpc())

    # ------------------------------------------------------------------
    # Patch PgVectorStore tool instance --------------------------------
    # ------------------------------------------------------------------
    # Provide dummy Supabase env so SupabaseConfig validation passes.
    monkeypatch.setenv("SUPABASE_URL", "http://stub.localhost")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-123")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-123")

    vector_store = PgVectorStore()
    stub_client = _StubClient(conn)
    monkeypatch.setattr(vector_store._tool, "_ensure_client", lambda: stub_client)
    monkeypatch.setenv("IS_SUPABASE_ENABLED", "false")  # skip connectivity check

    yield vector_store

    await conn.close()


# ---------------------------------------------------------------------------
# Tests ---------------------------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.asyncio
async def test_pgvector_upsert_and_query(store):  # noqa: D401 – test case
    scope = uuid.uuid4().hex  # unique per test run
    key = "doc-test"
    vector = _random_vector()

    # Upsert -----------------------------------------------------------
    await store.upsert(scope, key, vector, model_version="test-embedder")

    # Query ------------------------------------------------------------
    results = await store.query(scope, vector, k=1)

    assert results, "No results returned from pgvector query"
    assert results[0][0] == key
    # Distance should be approximately 0 since we query with same vector
    assert pytest.approx(results[0][1], abs=1e-6) == 0.0
