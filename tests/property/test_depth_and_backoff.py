import asyncio
from typing import Any, List

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.context import GraphContextManager
from ice_sdk.context.manager import GraphContext
from ice_sdk.models.node_models import ToolNodeConfig
from ice_sdk.tools.base import BaseTool
from ice_sdk.tools.service import ToolService


class ControlledFlakyTool(BaseTool):
    """Tool that fails a configurable number of times before succeeding."""

    name = "controlled_flaky"
    description = "Fails the first *n* times, then returns OK"

    def __init__(self, failures: int):
        super().__init__()
        self._remaining_failures = failures

    async def run(self, **kwargs: Any):  # type: ignore[override]
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise RuntimeError("Intentional failure – retry me")
        return {"ok": True}


# ---------------------------------------------------------------------------
# Depth-guard property test --------------------------------------------------
# ---------------------------------------------------------------------------


@given(
    num_nodes=st.integers(min_value=2, max_value=6),
    allowed_depth=st.integers(min_value=0, max_value=5),
)
@settings(deadline=None)  # async + I/O – disable per-example timing
@pytest.mark.asyncio
async def test_depth_guard_abort(num_nodes: int, allowed_depth: int) -> None:
    """Execution must abort when external depth_guard returns *False*."""

    # Build a linear chain `n0 -> n1 -> ... -> n{num_nodes-1}`
    nodes: List[ToolNodeConfig] = []
    for i in range(num_nodes):
        node = ToolNodeConfig(
            id=f"n{i}",
            name=f"node{i}",
            type="tool",
            tool_name="sum",
            tool_args={"numbers": [i]},
        )
        if i > 0:
            node.dependencies = [f"n{i-1}"]  # type: ignore[attr-defined]
            node.level = i  # type: ignore[attr-defined]
        nodes.append(node)

    # Register the builtin SumTool if not yet registered
    ts = ToolService()
    from ice_sdk.tools.builtins import SumTool

    ts.register(SumTool)  # idempotent

    # External depth_guard – only allow up to *allowed_depth* levels (1-indexed)
    def depth_guard(level_idx: int, _depth_ceiling: int | None) -> bool:  # noqa: ANN001
        return level_idx <= allowed_depth

    # Use a large depth_ceiling to ensure *depth_guard* is the limiting factor
    chain = ScriptChain(  # type: ignore[arg-type]
        nodes=nodes,  # type: ignore[arg-type]
        name="depth-guard-test",
        depth_ceiling=num_nodes + 10,
        depth_guard=depth_guard,
        tools=[SumTool()],
        context_manager=_mk_ctx_manager(),
    )

    result = await chain.execute()

    expected_success = allowed_depth >= num_nodes
    assert result.success is expected_success

    if not expected_success:
        assert result.error is not None and "Depth guard aborted" in result.error


# ---------------------------------------------------------------------------
# Retry back-off property test -----------------------------------------------
# ---------------------------------------------------------------------------


@given(
    base_backoff=st.floats(min_value=0.05, max_value=0.5),
    max_retries=st.integers(min_value=1, max_value=4),
)
@settings(deadline=None, suppress_health_check=(HealthCheck.function_scoped_fixture,))
@pytest.mark.asyncio
async def test_retry_backoff_timings(
    monkeypatch: pytest.MonkeyPatch, base_backoff: float, max_retries: int
) -> None:
    """Verify exponential back-off sleeps for each retry attempt."""

    sleep_calls: List[float] = []

    async def fake_sleep(delay: float) -> None:  # noqa: D401 – test helper
        sleep_calls.append(delay)
        # Return immediately without real waiting.

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    # One failure per retry; succeed on the last attempt
    tool = ControlledFlakyTool(failures=max_retries)

    node_cfg = ToolNodeConfig(
        id="t1",
        name="Controlled Flaky",
        tool_name="controlled_flaky",
        retries=max_retries,
        backoff_seconds=base_backoff,
    )

    chain = ScriptChain(  # type: ignore[arg-type]
        nodes=[node_cfg],  # type: ignore[arg-type]
        tools=[tool],
        name="retry-backoff-test",
        initial_context={"seed": 123},
        context_manager=_mk_ctx_manager(),
    )

    result = await chain.execute()

    assert result.success is True, "Chain should eventually succeed"

    # There should be exactly *max_retries* sleep invocations
    assert len(sleep_calls) == max_retries

    expected_delays = [base_backoff * (2**i) for i in range(max_retries)]
    # Compare floats with tolerance to avoid precision issues
    for observed, expected in zip(sleep_calls, expected_delays, strict=True):
        assert pytest.approx(expected, rel=1e-6) == observed


# ---------------------------------------------------------------------------
# Utilities ------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _mk_ctx_manager() -> GraphContextManager:
    """Return a fresh GraphContextManager with dummy session."""

    ctx_mgr = GraphContextManager()
    ctx_mgr.set_context(GraphContext(session_id="prop-test"))
    return ctx_mgr
