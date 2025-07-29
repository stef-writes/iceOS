from __future__ import annotations

"""Startup helper utilities for ice_api.

Provides a consolidated banner, component validation, and readiness flag
for the FastAPI application lifecycle.
"""

import importlib
import logging
import platform
import time
from datetime import datetime
from types import ModuleType
from typing import Any, Dict, Tuple

from ice_core.unified_registry import registry, global_agent_registry
from ice_core.models.enums import NodeType

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
        tool = registry.get_instance(NodeType.TOOL, name)
        if hasattr(tool, "get_input_schema"):
            tool.get_input_schema()
        if hasattr(tool, "get_output_schema"):
            tool.get_output_schema()
        return True, ""
    except Exception as exc:  # noqa: BLE001 – report any error
        return False, str(exc)


def validate_registered_components() -> Dict[str, Any]:
    """Validate registry contents; returns summary dict."""
    failed_tools: Dict[str, str] = {}
    for _, tool_name in registry.list_nodes(NodeType.TOOL):
        ok, err = _validate_tool(tool_name)
        if not ok:
            failed_tools[tool_name] = err
    return {
        "tool_failures": failed_tools,
        "tool_count": len(list(registry.list_nodes(NodeType.TOOL))),
        "agent_count": len(global_agent_registry.available_agents()),
        "workflow_count": len(list(registry.list_nodes(NodeType.WORKFLOW))),
    }


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
    "summarise_demo_load",
    "timed_import",
    "READY_FLAG",
] 