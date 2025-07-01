import asyncio
from typing import Any, Dict, List

import pytest

from ice_sdk.tools.base import ToolContext, function_tool

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
