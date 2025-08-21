from __future__ import annotations

import pytest


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for item in items:
        path = str(getattr(item, "fspath", ""))
        if "/tests/unit/" in path:
            item.add_marker(pytest.mark.unit)
        elif "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)


"""Global pytest configuration.

Auto-load the project‐level .env file (if present) so that integration
tests can access secrets such as OPENAI_API_KEY without requiring callers
to manually export them.  This keeps `pytest -q` behaviour identical to the
runtime where `python-dotenv` is commonly used.
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – optional dependency
    load_dotenv = None  # type: ignore


# ---------------------------------------------------------------------------
# Load .env file at repository root (if available) ---------------------------
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ENV_PATH = _REPO_ROOT / ".env"

if _ENV_PATH.exists() and load_dotenv is not None:
    load_dotenv(dotenv_path=_ENV_PATH, override=False)

# Ensure OPENAI_API_KEY propagates to child processes (if any) --------------
if "OPENAI_API_KEY" in os.environ:
    os.environ.setdefault("OPENAI_API_KEY", os.environ["OPENAI_API_KEY"])

# Default to allowing the dev token in integration tests unless a test overrides it.
# This keeps local/CI integration flows simple while auth-hardening tests can
# explicitly set ICE_ALLOW_DEV_TOKEN=0 as needed.
os.environ.setdefault("ICE_ALLOW_DEV_TOKEN", "1")

# Ensure project source is importable when root package is not installed -----
_SRC_PATH = _REPO_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))


# ---------------------------------------------------------------------------
# Test isolation fixtures ----------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_llm_registry() -> None:
    """Ensure LLM factory registry is isolated per test.

    Many integration tests register different LLM factories under the same
    model name (e.g., "gpt-4o"). The unified registry is process-global, so we
    clear LLM factories between tests to avoid cross-test interference.
    """
    from ice_core.unified_registry import clear_llm_factories, clear_tool_factories

    clear_llm_factories()
    clear_tool_factories()
    # Tests that need tools should load them via plugin manifests explicitly
    yield
    clear_llm_factories()
    clear_tool_factories()
