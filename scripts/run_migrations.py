from __future__ import annotations

"""Run Alembic migrations programmatically.

Usage::

    poetry run python scripts/run_migrations.py
"""

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

ALEMBIC_INI_PATH = ROOT / "alembic.ini"


def _upgrade_head() -> None:  # noqa: D401
    cfg = Config(str(ALEMBIC_INI_PATH))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option(
        "sqlalchemy.url", os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./iceos.db")
    )
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    _upgrade_head()
