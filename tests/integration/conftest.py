"""Pytest configuration for integration tests.

Provides fixtures for Redis integration testing using Docker containers and
bootstraps the in-process plugin registry so tools are available to the
orchestrator runtime in tests that do not start the API server.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator

import pytest
import sqlalchemy as sa
import pytest_asyncio
import logging

try:
    import redis.asyncio as redis  # type: ignore

    HAS_REDIS = True
except Exception:
    HAS_REDIS = False

try:
    from testcontainers.redis import RedisContainer

    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False
    RedisContainer = None


# Removed custom event_loop fixture to let pytest-asyncio handle it automatically
# when using asyncio_mode = auto
# Tone down noisy SQLAlchemy pool logs that can fire after event loop shutdown
try:
    _pool_logger = logging.getLogger("sqlalchemy.pool")
    _pool_logger.setLevel(logging.ERROR)
    _pool_logger.propagate = False
    _np_logger = logging.getLogger("sqlalchemy.pool.impl.NullPool")
    _np_logger.setLevel(logging.ERROR)
    _np_logger.propagate = False
except Exception:
    pass


@pytest.fixture(scope="session", autouse=True)
def _ensure_db_schema() -> None:
    """Ensure Alembic schema is upgraded to head for the configured DB.

    - Derives a sync DSN from DATABASE_URL when ALEMBIC_SYNC_URL is not set
    - Runs `alembic upgrade head` programmatically
    """
    # Only run if a DB is configured
    db_url = os.getenv("DATABASE_URL") or os.getenv("ICEOS_DB_URL")
    sync_url = os.getenv("ALEMBIC_SYNC_URL")
    if not sync_url and db_url:
        # Convert to psycopg2 driver for Alembic
        if db_url.startswith("postgresql+asyncpg://"):
            sync_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        elif db_url.startswith("postgresql://"):
            sync_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        else:
            sync_url = db_url
    if not sync_url:
        return
    try:
        from alembic import command  # type: ignore
        from alembic.config import Config  # type: ignore

        ini_path = Path(__file__).parents[2] / "alembic.ini"
        cfg = Config(str(ini_path))
        # Force URL to target the same DB the tests will use
        cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(cfg, "head")
        # Verify critical tables exist after upgrade
        try:
            engine = sa.create_engine(sync_url)
            with engine.connect() as conn:
                # to_regclass returns NULL if relation does not exist
                exists = conn.execute(sa.text("SELECT to_regclass('semantic_memory') IS NOT NULL")).scalar()
                if not bool(exists):
                    raise RuntimeError("semantic_memory table not present after alembic upgrade")
        except Exception as ver_exc:
            raise RuntimeError(f"alembic upgrade verification failed: {ver_exc}")
    except Exception as exc:
        raise RuntimeError(f"[itest] alembic upgrade failed for DSN: {sync_url} – {exc}")


@pytest.fixture(scope="session", autouse=True)
def _dispose_engines_on_session_end(request: pytest.FixtureRequest) -> None:
    """Dispose async engines at session end to avoid GC warnings/logging errors."""
    try:
        import anyio

        async def _dispose() -> None:
            try:
                from ice_api.db.database_session_async import dispose_all_engines

                await dispose_all_engines()
            except Exception:
                pass

        def _finalizer() -> None:
            try:
                anyio.run(_dispose)
            except Exception:
                pass

        request.addfinalizer(_finalizer)
    except Exception:
        # Best-effort; tests still pass without this
        pass


@pytest.fixture(autouse=True)
async def _dispose_engines_after_each_test():
    """Ensure no checked-out connections remain between tests.

    This aggressively disposes async engines after each test to eliminate
    teardown GC warnings when event loops switch (asyncio/trio).
    """
    yield
    try:
        from ice_api.db.database_session_async import dispose_all_engines

        await dispose_all_engines()
    except Exception:
        pass


@pytest_asyncio.fixture(scope="session")
async def redis_container():
    """Provide a Redis container for integration tests.

    This fixture starts a Redis Docker container that persists for the entire
    test session. The container is automatically cleaned up after tests complete.
    """
    if not HAS_TESTCONTAINERS or not HAS_REDIS:
        pytest.skip(
            "redis/testcontainers not available - install with: pip install redis testcontainers"
        )

    with RedisContainer() as container:
        yield container


@pytest_asyncio.fixture
async def redis_client(redis_container) -> AsyncGenerator[object, None]:
    """Provide an async Redis client connected to the test container.

    This fixture creates a new Redis client for each test, ensuring test isolation.
    The client is automatically closed after the test completes.
    """
    # Get connection details
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)

    client = redis.from_url(f"redis://{host}:{port}/0", decode_responses=True)

    # Ensure clean state
    await client.flushdb()

    yield client

    # Cleanup
    await client.close()


@pytest.fixture
def redis_url(redis_container) -> str:
    """Provide the Redis connection URL for tests that need it."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"


# ---------------------------------------------------------------------------
# Global plugin bootstrap for integration tests (session, autouse)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _itest_env_defaults() -> None:
    """Session-wide sane defaults for integration tests.

    Ensures deterministic providers and in-process-friendly execution when tests
    run via TestClient or outside Docker.
    """
    os.environ.setdefault("ICEOS_EMBEDDINGS_PROVIDER", "hash")
    os.environ.setdefault("ICE_ECHO_LLM_FOR_TESTS", "1")
    os.environ.setdefault("ICE_EXEC_SYNC_FOR_TESTS", "1")
    os.environ.setdefault("ICE_STRICT_SERIALIZATION", "1")


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_plugins() -> None:
    """Load first-party tools via manifest for orchestrator-only tests.

    Ensures tools like `writer_tool` are registered in the unified registry
    even when the FastAPI app (which normally loads plugins) is not running.
    """
    try:
        from ice_core.registry import registry
    except Exception:
        return

    manifests = [
        Path(__file__).parents[2] / "plugins/kits/tools/memory/plugins.v0.yaml",
        Path(__file__).parents[2] / "plugins/kits/tools/search/plugins.v0.yaml",
    ]
    os.environ["ICEOS_PLUGIN_MANIFESTS"] = ",".join(str(m) for m in manifests)
    try:
        for m in manifests:
            registry.load_plugins(str(m), allow_dynamic=True)
    except Exception:
        # Tests that explicitly manage plugin loading can proceed regardless
        pass
