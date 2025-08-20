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

from sqlalchemy import engine_from_config, pool, text

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


def _sync_url_from_env() -> str:
    """Return a sync SQLAlchemy URL for Alembic.

    Prefers ALEMBIC_SYNC_URL; falls back to DATABASE_URL after normalizing
    common async forms to sync.
    """

    url = os.getenv("ALEMBIC_SYNC_URL") or os.getenv("DATABASE_URL", "")
    url = url.replace("+asyncpg", "")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    # sqlite and other schemes pass through
    return url


_db_url = _sync_url_from_env() or "sqlite:///./iceos.db"
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


def _ensure_alembic_version_compat(connection) -> None:
    """Ensure alembic_version exists and can store long revision ids.

    Some older DBs may have version_num as VARCHAR(32). We widen to 255 to
    support longer revision identifiers before applying upgrades.
    """
    try:
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(255) PRIMARY KEY)"
            )
        )
    except Exception:
        pass
    try:
        connection.execute(
            text(
                "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
            )
        )
    except Exception:
        # Table may not exist yet in fresh DB; harmless
        pass


def run_migrations_online() -> None:
    """Run migrations in "online" mode – direct DB connection."""

    connectable = engine_from_config(  # type: ignore[arg-type]
        config.get_section(config.config_ini_section, {}),  # type: ignore[arg-type]
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Pre-check alembic_version table/column width for robust upgrades
        _ensure_alembic_version_compat(connection)
        context.configure(  # type: ignore[attr-type]
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():  # type: ignore[attr-defined]
            context.run_migrations()  # type: ignore[attr-defined]


if context.is_offline_mode():  # type: ignore[attr-defined]
    run_migrations_offline()
else:
    run_migrations_online()
