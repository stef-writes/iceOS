from __future__ import annotations

import os
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _get_database_url() -> Optional[str]:
    url = os.getenv("DATABASE_URL") or os.getenv("ICEOS_DB_URL")
    if not url:
        return None
    # Ensure async driver for SQLAlchemy
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_engine() -> Optional[AsyncEngine]:
    global _engine
    if _engine is not None:
        return _engine
    url = _get_database_url()
    if not url:
        return None
    _engine = create_async_engine(
        url,
        echo=os.getenv("DB_ECHO", "0") == "1",
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        pool_pre_ping=True,
    )
    return _engine


def get_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    engine = get_engine()
    if engine is None:
        return None
    _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


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
            await conn.execute("SELECT 1")  # type: ignore[arg-type]
        return True
    except Exception:
        return False
