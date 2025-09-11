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
    """Register an echo LLM for deterministic tests when explicitly enabled.

    Enabled only if ICE_ECHO_LLM_FOR_TESTS=1. No-ops otherwise.
    """
    try:
        if os.getenv("ICE_ECHO_LLM_FOR_TESTS", "0") == "1":
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
    """No-op: migrations must be run out-of-band via Makefile/Compose.

    This keeps app startup fast and deterministic.
    """
    return
