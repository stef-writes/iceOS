from __future__ import annotations

"""Alembic migration environment.

Run via ``python -m alembic upgrade head`` or programmatically through
`scripts/run_migrations.py`.

The script pulls metadata from ``services.models.Base`` so that future
`alembic revision --autogenerate -m "…"` picks up schema changes.
"""

import os
import sys
from logging.config import fileConfig
from os import environ
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context  # type: ignore

# Add src/ to path for "services" package imports ---------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "src"))

# When building documentation on Read the Docs we need the *src/* directory on
# the path *before* Sphinx imports modules.  The READTHEDOCS env var is set to
# "True" during the build process.
if environ.get("READTHEDOCS") == "True":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Alembic config -------------------------------------------------------------
# ---------------------------------------------------------------------------

config = context.config  # type: ignore[attr-defined]
fileConfig(config.config_file_name)  # type: ignore[arg-type]

_db_url = os.getenv("DATABASE_URL", "sqlite:///./iceos.db")
# Force sync driver for Alembic (replace async drivers)
if "+asyncpg" in _db_url:
    _db_url = _db_url.replace("+asyncpg", "+psycopg2")
if _db_url.startswith("sqlite+aiosqlite"):
    _db_url = _db_url.replace("sqlite+aiosqlite", "sqlite", 1)
config.set_main_option("sqlalchemy.url", _db_url)

# Import ORM metadata from API DB models
from ice_api.db.orm_models_core import Base  # noqa: E402

target_metadata = Base.metadata  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Offline & online routines --------------------------------------------------
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run "offline" migrations – emit SQL to script instead of DB."""

    url = config.get_main_option("sqlalchemy.url")
    context.configure(  # type: ignore[arg-type]
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():  # type: ignore[attr-defined]
        context.run_migrations()  # type: ignore[attr-defined]


def run_migrations_online() -> None:
    """Run migrations in "online" mode – direct DB connection."""

    connectable = engine_from_config(  # type: ignore[arg-type]
        config.get_section(config.config_ini_section, {}),  # type: ignore[arg-type]
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(  # type: ignore[attr-type]
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():  # type: ignore[attr-defined]
            context.run_migrations()  # type: ignore[attr-defined]


if context.is_offline_mode():  # type: ignore[attr-defined]
    run_migrations_offline()
else:
    run_migrations_online()
