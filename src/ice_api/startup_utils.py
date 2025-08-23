from __future__ import annotations

"""Startup helper utilities for ice_api.

Provides a consolidated banner, component validation, and readiness flag
for the FastAPI application lifecycle.
"""

import importlib
import logging
import os
import platform
import time
from datetime import datetime
from types import ModuleType
from typing import Any, Dict, Tuple

from ice_core.registry import global_agent_registry, registry

logger = logging.getLogger(__name__)


READY_FLAG: bool = False  # updated by main.lifespan


def _ascii_bar(text: str, width: int = 60) -> str:
    pad = max(0, width - len(text) - 2)
    return f"╭{'─' * pad} {text} "


def print_startup_banner(app_version: str, git_sha: str | None = None) -> None:
    """Print a single consolidated startup banner."""
    banner_lines = [
        "",
        _ascii_bar(" iceOS STARTUP " + (f"[{git_sha[:7]}]" if git_sha else "")),
        f"│ Version     : {app_version}",
        f"│ Python      : {platform.python_version()} - {platform.system()} {platform.release()}",
        f"│ Start time  : {datetime.utcnow().isoformat()}Z",
        f"│ PID         : {os.getpid()}",
        "╰" + "─" * 60,
        "",
    ]
    for line in banner_lines:
        logger.info(line)


# ---------------------------------------------------------------------------
# Component validation helpers
# ---------------------------------------------------------------------------


def _validate_tool(name: str) -> Tuple[bool, str]:
    try:
        # Instantiate via factory to validate real tool behavior
        tool = registry.get_tool_instance(name)
        if hasattr(tool, "get_input_schema"):
            tool.get_input_schema()
        if hasattr(tool, "get_output_schema"):
            tool.get_output_schema()
        return True, ""
    except Exception as exc:  # noqa: BLE001 – report any error
        return False, str(exc)


def validate_registered_components() -> Dict[str, Any]:
    """Validate registry contents; returns summary dict."""
    # Zero-setup: ensure first-party generated tools are imported so factories register
    # Starter packs load via ICEOS_PLUGIN_MANIFESTS; avoid implicit imports
    failed_tools: Dict[str, str] = {}
    # Prefer factory-registered tools for validation
    tool_names = [name for name, _ in registry.available_tool_factories()]
    for tool_name in tool_names:
        ok, err = _validate_tool(tool_name)
        if not ok:
            failed_tools[tool_name] = err
    return {
        "tool_failures": failed_tools,
        "tool_count": len(tool_names),
        "agent_count": len(global_agent_registry.available_agents()),
        "workflow_count": len(registry.available_workflow_factories()),
    }


def maybe_register_echo_llm_for_tests() -> None:
    """Register an echo LLM for deterministic tests when enabled.

    Enabled if ICE_ECHO_LLM_FOR_TESTS=1 or ICE_API_TOKEN is the dev token.
    No-ops in production.
    """
    try:
        if (
            os.getenv("ICE_ECHO_LLM_FOR_TESTS", "0") == "1"
            or os.getenv("ICE_API_TOKEN") == "dev-token"
        ):
            from ice_core.unified_registry import (
                register_llm_factory as _reg_llm,  # type: ignore
            )

            _reg_llm("gpt-4o", "scripts.ops.verify_runtime:create_echo_llm")
            logger.info("Registered echo LLM factory for tests (gpt-4o)")
    except Exception:  # pragma: no cover – best-effort
        logger.debug("Echo LLM registration skipped", exc_info=True)


# ---------------------------------------------------------------------------
# Demo loading utilities
# ---------------------------------------------------------------------------


def timed_import(module_path: str) -> Tuple[float, ModuleType | None, Exception | None]:
    """Import *module_path* while measuring wall-time."""
    start = time.perf_counter()
    try:
        mod = importlib.import_module(module_path)
        return time.perf_counter() - start, mod, None
    except Exception as exc:  # noqa: BLE001
        return time.perf_counter() - start, None, exc


def summarise_demo_load(label: str, seconds: float, ok: bool, detail: str = "") -> None:
    status = "✅" if ok else "⚠️ "
    logger.info(f"{status}  {label:<25} {seconds*1000:>6.0f} ms  {detail}")


__all__ = [
    "print_startup_banner",
    "validate_registered_components",
    "maybe_register_echo_llm_for_tests",
    "summarise_demo_load",
    "timed_import",
    "READY_FLAG",
]


async def run_alembic_migrations_if_enabled() -> None:
    """Run Alembic upgrade to head when enabled via env flag.

    Controlled by ICEOS_RUN_MIGRATIONS=1 and only when DATABASE_URL is set.
    """
    require_db = os.getenv("ICEOS_REQUIRE_DB", "0") == "1"
    if os.getenv("ICEOS_RUN_MIGRATIONS", "0") != "1":
        # If DB is required for startup, fail early when migrations are disabled
        if require_db:
            raise RuntimeError("ICEOS_REQUIRE_DB=1 is set but ICEOS_RUN_MIGRATIONS!=1")
        return
    if not os.getenv("DATABASE_URL") and not os.getenv("ICEOS_DB_URL"):
        if require_db:
            raise RuntimeError(
                "ICEOS_REQUIRE_DB=1 is set but no DATABASE_URL/ICEOS_DB_URL configured"
            )
        return
    try:
        # In some minimal test contexts (e.g., TestClient in test image), alembic.ini
        # is not present. Skip migrations gracefully in that case.
        import pathlib as _pathlib

        if not _pathlib.Path("alembic.ini").exists():
            logger.warning(
                "alembic.ini not found – skipping migrations in this context"
            )
            return
        from alembic import command  # type: ignore
        from alembic.config import Config  # type: ignore

        cfg = Config("alembic.ini")
        # Log script location and env URL for diagnostics
        logger.info(
            "Alembic script_location=%s", cfg.get_main_option("script_location")
        )
        logger.info("Alembic DATABASE_URL=%s", os.getenv("DATABASE_URL"))
        # Force sync DSN for Alembic (psycopg2) based on env
        db_url = os.getenv("DATABASE_URL", "").strip()
        if db_url.startswith("postgresql+asyncpg"):
            db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        if db_url:
            cfg.set_main_option("sqlalchemy.url", db_url)
        # Ensure version table exists (no-op if present), then upgrade
        try:
            command.ensure_version(cfg)
        except Exception:
            logger.exception("Alembic ensure_version raised")

        # If schema already contains the columns introduced by the latest
        # migration but the alembic_version table wasn't advanced (e.g., a
        # manual hotfix added columns), stamp head instead of re-applying.
        _prechecked_stamp: bool = False
        try:
            from sqlalchemy import text as _sql_text

            sync_url = cfg.get_main_option("sqlalchemy.url")
            if sync_url:
                import sqlalchemy as _sa

                eng = _sa.create_engine(sync_url)
                with eng.connect() as conn:  # type: ignore[misc]
                    q = _sql_text(
                        """
                        SELECT
                          SUM(CASE WHEN table_name='components' AND column_name='user_id' THEN 1 ELSE 0 END) +
                          SUM(CASE WHEN table_name='components' AND column_name='tags' THEN 1 ELSE 0 END) +
                          SUM(CASE WHEN table_name='blueprints' AND column_name='user_id' THEN 1 ELSE 0 END) +
                          SUM(CASE WHEN table_name='blueprints' AND column_name='tags' THEN 1 ELSE 0 END) AS cnt
                        FROM information_schema.columns
                        WHERE table_schema='public' AND table_name IN ('components','blueprints')
                          AND column_name IN ('user_id','tags')
                        """
                    )
                    cnt = int(conn.execute(q).scalar() or 0)
                    if cnt >= 4:
                        try:
                            command.stamp(cfg, "head")
                            _prechecked_stamp = True
                            logger.info(
                                "Alembic stamped to head based on existing columns"
                            )
                        except Exception:
                            logger.exception("Alembic stamp head failed")
        except Exception:
            logger.debug("Pre-upgrade schema inspection failed", exc_info=True)

        if not _prechecked_stamp:
            try:
                command.upgrade(cfg, "head")
            except Exception:
                logger.exception("Alembic upgrade head failed")
                raise

        # Hard guard: verify alembic head applied and semantic_memory table exists
        from sqlalchemy import text

        from ice_api.db.database_session_async import (
            get_applied_migration_head,
            get_engine,
        )

        head = await get_applied_migration_head()
        logger.info("Alembic applied_head=%s", head)
        engine = get_engine()
        if engine is None:
            raise RuntimeError("No database engine available after migration")

        async def _schema_exists() -> bool:
            try:
                async with engine.connect() as conn:  # type: ignore[call-arg]
                    q = text(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='semantic_memory')"
                    )
                    res = await conn.execute(q)
                    return bool(res.scalar())
            except Exception:
                return False

        if not await _schema_exists():
            logger.warning(
                "Primary migration verification failed; attempting offline SQL fallback"
            )

            # Fallback: generate offline SQL and apply via psycopg2 synchronously for robustness
            import os as _os
            import shlex as _shlex
            import subprocess as _sp
            from typing import List as _List

            cmd = f"alembic -c { _shlex.quote(cfg.config_file_name or 'alembic.ini') } upgrade head --sql"
            cp = _sp.run(cmd, shell=True, capture_output=True, text=True)  # noqa: S603
            if cp.returncode != 0:
                raise RuntimeError(f"alembic --sql failed: {cp.stderr}")
            sql_text = cp.stdout

            import re as _re

            import psycopg2 as _pg

            dsn = _os.getenv("DATABASE_URL", "").strip()
            if dsn.startswith("postgresql+asyncpg"):
                dsn = dsn.replace("postgresql+asyncpg", "postgresql", 1)
            if not dsn.startswith("postgresql://"):
                raise RuntimeError(
                    "DATABASE_URL must be a Postgres DSN for offline SQL fallback"
                )
            conn = _pg.connect(dsn)
            conn.autocommit = True
            cur = conn.cursor()
            stmts: _List[str] = [
                s.strip() for s in _re.split(r";\s*\n", sql_text) if s.strip()
            ]
            for stmt in stmts:
                try:
                    cur.execute(stmt)
                except Exception:
                    # Continue applying best-effort; extension creation may fail if lacking perms
                    pass
            cur.close()
            conn.close()

            if not await _schema_exists():
                raise RuntimeError(
                    "Offline SQL fallback did not create required tables"
                )

        # Post-migration hardening: ensure newly added columns exist even if
        # the Alembic revision table is stale or the upgrade was partially applied.
        try:
            # Use transactional block to ensure DDL is committed
            async with engine.begin() as conn:  # type: ignore[call-arg]
                for stmt in (
                    # Components: user_id, tags
                    "ALTER TABLE components ADD COLUMN IF NOT EXISTS user_id VARCHAR(64)",
                    "ALTER TABLE components ADD COLUMN IF NOT EXISTS tags JSON",
                    # Blueprints: user_id, tags
                    "ALTER TABLE blueprints ADD COLUMN IF NOT EXISTS user_id VARCHAR(64)",
                    "ALTER TABLE blueprints ADD COLUMN IF NOT EXISTS tags JSON",
                ):
                    try:
                        await conn.execute(text(stmt))
                    except Exception:
                        # Best-effort; continue with next statement
                        pass
        except Exception:
            # Do not fail startup if hardening step encounters issues
            logger.debug("Column hardening step skipped", exc_info=True)
        # If table exists but head is None, log a warning instead of failing hard.
        if head is None:
            logger.warning(
                "Alembic head is None but schema is present; proceeding. Consider running 'alembic stamp head' to record the current revision."
            )
    except Exception as exc:  # pragma: no cover
        logger.warning("Alembic migration/verification failed: %s", exc)
        raise
