import asyncio
from typing import Any, Dict, List

import httpx
import pytest

# ---------------------------------------------------------------------------
# Global shims to keep legacy tests working after the ScriptChain→Workflow rename
# ---------------------------------------------------------------------------
from ice_orchestrator.workflow import Workflow  # noqa: F401


def model_json_schema(model_cls):  # noqa: D401 – test helper
    """Return JSON schema for *model_cls* (compat shim for legacy tests)."""

    return model_cls.model_json_schema()


def load_example_chain(_path):  # noqa: D401 – placeholder used by training-data tests
    """Return empty chain payload for training-data tests (placeholder)."""

    return {}

from ice_sdk.skills import ToolContext, function_tool
from ice_sdk.skills.base import SkillBase

# AgentFactory exposed for tests requiring it -------------------------------
from ice_sdk.utils.agent_factory import AgentFactory

# ruff: noqa: E402

# ---------------------------------------------------------------------------
# Test-only deterministic Slack replacement  ---------------------------------
# ---------------------------------------------------------------------------

_CALL_LOG: List[Dict[str, Any]] = []


@function_tool(name_override="slack_post")
async def _dummy_slack(ctx: ToolContext, channel: str, text: str) -> Dict[str, Any]:  # type: ignore[override]
    """Deterministic replacement used across test-suite."""
    _CALL_LOG.append({"channel": channel, "text": text})
    # Simulate minimal API latency ------------------------------------------------
    await asyncio.sleep(0)
    return {"sent": True}


# pylint: disable=unused-argument


@pytest.fixture(name="isolated_slack_tool")
async def fixture_isolated_slack_tool() -> Any:  # type: ignore[override]
    """Returns the dummy slack tool and clears the call-log **after** each test.

    Usage::

        async def test_flow(isolated_slack_tool):
            chain = ScriptChain(nodes=..., tools=[isolated_slack_tool])
            result = await chain.execute()
            assert len(isolated_slack_tool.call_log) == 1
    """

    # Expose call-log on the tool instance for convenience ----------------------
    _dummy_slack.call_log = _CALL_LOG  # type: ignore[attr-defined]
    yield _dummy_slack  # noqa: E501 – yield to test
    _CALL_LOG.clear()


# ---------------------------------------------------------------------------
# Dynamic marker assignment --------------------------------------------------
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config, items):  # noqa: D401
    """Automatically mark *contract* and *property* tests as *slow* so they can
    be excluded from the default CI run with ``-m 'not slow'``.
    """

    import pathlib

    for item in items:
        node_path = pathlib.Path(item.fspath.strpath)
        if "contract" in item.keywords or "property" in str(node_path.parts):
            item.add_marker(pytest.mark.slow)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Architectural guard & shim enforcement ------------------------------------
# ---------------------------------------------------------------------------


# Ensure project root is on PYTHONPATH for ``scripts``


@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    # Mock all external HTTP calls
    def mock_httpx(*args, **kwargs):
        return httpx.Response(200, json={"mock": "data"})

    monkeypatch.setattr(httpx, "get", mock_httpx)
    monkeypatch.setattr(httpx, "post", mock_httpx)

    # Mock secret manager
    monkeypatch.setattr("ice_sdk.utils.secrets.get_secret", lambda key: f"mock_{key}")


# ---------------------------------------------------------------------------
# Additional fixtures for deterministic skill execution ----------------------
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mock_skill_execution(monkeypatch):  # noqa: D401 – fixture
    """Monkeypatch :py:meth:`SkillBase.execute` to return dummy data.

    Prevents real external requests inside skills during the unit test run.
    """

    async def _fake_execute(self: SkillBase, *args, **kwargs):  # type: ignore[no-self-use]
        await asyncio.sleep(0)
        return {"mock": "data"}

    monkeypatch.setattr(SkillBase, "execute", _fake_execute)
    yield


@pytest.fixture(name="agent_factory")
def fixture_agent_factory():  # noqa: D401 – fixture
    """Expose the central AgentFactory for tests needing AgentConfig stubs."""

    return AgentFactory
