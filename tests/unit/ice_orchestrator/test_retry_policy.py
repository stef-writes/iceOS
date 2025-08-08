from typing import Any, Dict

import pytest
from pydantic import BaseModel

from ice_core.models.node_models import NodeExecutionResult, RetryPolicy
from ice_core.unified_registry import register_node
from ice_orchestrator.execution.node_runtime_executor import NodeExecutor

# ---------------------------------------------------------------------------
# Dummy executor that fails twice, succeeds on third call
# ---------------------------------------------------------------------------
_attempt_counter = {"count": 0}


@register_node("dummy")  # registers with unified registry
async def _dummy_executor(_wf, _cfg, _ctx):  # noqa: D401 – test stub
    _attempt_counter["count"] += 1
    if _attempt_counter["count"] < 3:
        raise RuntimeError("temporary failure")
    from ice_core.models.node_metadata import NodeMetadata

    return NodeExecutionResult(  # type: ignore[call-arg]
        success=True,
        output={"ok": True},
        metadata=NodeMetadata(node_id="n1", node_type="dummy"),
    )


# ---------------------------------------------------------------------------
# Minimal chain stub with required attributes for NodeExecutor
# ---------------------------------------------------------------------------
class _FakeContextManager:
    class _Ctx:
        execution_id = None

    def get_context(self):
        return self._Ctx()

    def update_node_context(self, **kwargs):
        pass


class _FakeBudget:
    def __getattr__(self, item):  # noqa: D401 – catch-all no-op
        return lambda *a, **k: None


class _FakeChain:
    def __init__(self, node):
        self.nodes = {node.id: node}
        self.use_cache = False
        self._cache: Dict[str, Any] = {}
        self.context_manager = _FakeContextManager()
        self.failure_policy = type("FP", (), {"name": "HALT"})()
        self.budget = _FakeBudget()
        self.persist_intermediate_outputs = False
        self.validate_outputs = False

    # Needed by NodeExecutor
    def _emit_event(self, *_, **__):
        pass


# ---------------------------------------------------------------------------
# Minimal Node config stub
# ---------------------------------------------------------------------------
class DummyNode(BaseModel):
    id: str = "n1"
    type: str = "dummy"
    retry_policy: RetryPolicy = RetryPolicy(
        max_attempts=3, backoff_seconds=0.0, backoff_strategy="fixed"
    )
    timeout_seconds: int = 5
    output_schema: dict = {}

    def runtime_validate(self):
        pass


@pytest.mark.asyncio
async def test_retry_policy_success_after_retries():
    global _attempt_counter
    _attempt_counter["count"] = 0

    node = DummyNode()
    chain = _FakeChain(node)
    executor = NodeExecutor(chain)

    result = await executor.execute_node("n1", {})

    assert result.success is True
    # Executor should have been called 3 times (2 failures + 1 success)
    assert _attempt_counter["count"] == 3
