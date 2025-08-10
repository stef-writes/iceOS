from __future__ import annotations

"""Global pytest configuration.

Auto-load the project‐level .env file (if present) so that integration
tests can access secrets such as OPENAI_API_KEY without requiring callers
to manually export them.  This keeps `pytest -q` behaviour identical to the
runtime where `python-dotenv` is commonly used.
"""

import os
from pathlib import Path

import pytest

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
    from ice_orchestrator.plugins import load_first_party_tools

    clear_llm_factories()
    clear_tool_factories()
    # Re-register built-in tools deterministically for tests that expect them
    try:
        load_first_party_tools()
    except Exception:
        pass
    yield
    clear_llm_factories()
    clear_tool_factories()
