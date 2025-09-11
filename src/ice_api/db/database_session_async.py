from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator, Dict, Optional
from contextlib import asynccontextmanager

from sqlalchemy import text
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

_engines: Dict[int, AsyncEngine] = {}
_session_factories: Dict[int, async_sessionmaker[AsyncSession]] = {}


def _strip_query_param(url: str, name: str) -> str:
    parts = urlsplit(url)
    if not parts.query:
        return url
    q = [(k, v) for (k, v) in parse_qsl(parts.query, keep_blank_values=True) if k != name]
    new_query = urlencode(q, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def _get_database_url() -> Optional[str]:
    url = os.getenv("DATABASE_URL") or os.getenv("ICEOS_DB_URL")
    if not url:
        return None
    # Normalize driver: prefer asyncpg for runtime engine
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # asyncpg does not accept sslmode in query params – strip if present
    if "+asyncpg://" in url:
        url = _strip_query_param(url, "sslmode")
    return url


def _loop_key() -> int:
    try:
        return id(asyncio.get_running_loop())
    except RuntimeError:
        # No running loop; treat as singleton context
        return 0


def get_engine() -> Optional[AsyncEngine]:
    key = _loop_key()
    if key in _engines:
        return _engines[key]
    url = _get_database_url()
    if not url:
        return None
    # Use NullPool to avoid cross-event-loop issues in async tests and ASGI transports
    engine = create_async_engine(
        url,
        echo=os.getenv("DB_ECHO", "0") == "1",
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    _engines[key] = engine
    return engine


def get_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    key = _loop_key()
    if key in _session_factories:
        return _session_factories[key]
    engine = get_engine()
    if engine is None:
        return None
    factory = async_sessionmaker(engine, expire_on_commit=False)
    _session_factories[key] = factory
    return factory


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL not configured – SQL session unavailable")
    async with factory() as session:
        yield session


async def check_connection() -> bool:
    engine = get_engine()
    if engine is None:
        return False
    try:
        async with engine.connect() as conn:  # type: ignore[call-arg]
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def get_applied_migration_head() -> str | None:
    """Return the applied Alembic head version from the database, if present.

    Returns None when the alembic_version table does not exist or on error.
    """
    engine = get_engine()
    if engine is None:
        return None
    try:
        async with engine.connect() as conn:  # type: ignore[call-arg]
            # Check if alembic_version table exists first to avoid noisy errors
            exists = await conn.execute(
                text("SELECT to_regclass('alembic_version') IS NOT NULL")
            )
            exists_row = exists.first()
            if not exists_row or exists_row[0] is not True:
                return None
            result = await conn.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            row = result.first()
            return str(row[0]) if row else None
    except Exception:
        return None

async def dispose_all_engines() -> None:
    """Dispose all async engines and clear session factories.

    Helps prevent GC warnings about unclosed connections when event loops
    finish (e.g., ASGI/pytest transports).
    """
    # Dispose engines per loop key and clear factories to avoid reuse
    keys = list(_engines.keys())
    for key in keys:
        eng = _engines.get(key)
        if eng is None:
            continue
        try:
            await eng.dispose()
        except Exception:
            pass
        _engines.pop(key, None)
        _session_factories.pop(key, None)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Async context manager that yields an AsyncSession and ensures close.

    Prefer this over iterating ``get_session()`` to guarantee explicit return
    of connections to the pool before event loop teardown.
    """
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL not configured – SQL session unavailable")
    async with factory() as session:
        yield session
