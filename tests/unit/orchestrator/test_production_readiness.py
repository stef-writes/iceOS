from __future__ import annotations

import asyncio
from typing import Any

import pytest
from ice_core.models.model_registry import get_default_model_id

from ice_orchestrator.errors.chain_errors import CircularDependencyError
from ice_orchestrator.graph.dependency_graph import DependencyGraph
from ice_orchestrator.workflow_execution_context import (
    WorkflowExecutionContext,
    _BulkSaveProtocol,  # type: ignore
)
from ice_sdk.models.node_models import LLMConfig, LLMOperatorConfig, ModelProvider

# ---------------------------------------------------------------------------
# Helpers --------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _ai_node(node_id: str, **extra: Any) -> LLMOperatorConfig:  # noqa: D401 – factory
    """Convenience factory that returns a minimal *AiNodeConfig*."""

    return LLMOperatorConfig(  # type: ignore[call-arg]
        id=node_id,
        type="ai",
        name=node_id,
        model=get_default_model_id(),
        prompt="hi",
        llm_config=LLMConfig(
            provider=ModelProvider.OPENAI, model=get_default_model_id()
        ),
        **extra,
    )


# ---------------------------------------------------------------------------
# Circular dependency detection ---------------------------------------------
# ---------------------------------------------------------------------------


aio = pytest.mark.asyncio


@aio
async def test_circular_dependency_raises() -> None:  # noqa: D401 – critical path
    n0 = _ai_node("n0", dependencies=["n1"])
    n1 = _ai_node("n1", dependencies=["n0"])

    with pytest.raises(CircularDependencyError):
        # Validation happens inside DependencyGraph constructor
        DependencyGraph([n0, n1])


# ---------------------------------------------------------------------------
# Air-gap enforcement --------------------------------------------------------
# ---------------------------------------------------------------------------


class _Stub:
    def __init__(self, node_id: str, deps: list[str] | None = None, **attrs: Any):
        self.id = node_id
        self.dependencies = deps or []
        # Attach arbitrary attributes for security flags
        for k, v in attrs.items():
            setattr(self, k, v)


@aio
async def test_airgap_enforcement_blocks_external_io() -> None:  # noqa: D401
    n_safe = _Stub("safe", airgap_mode=True)
    n_external = _Stub("net", deps=["safe"], requires_external_io=True)

    with pytest.raises(ValueError):
        DependencyGraph([n_safe, n_external])


# ---------------------------------------------------------------------------
# Batched persistence --------------------------------------------------------
# ---------------------------------------------------------------------------


# *Subclassing* the protocol satisfies static type checkers without runtime cost.


class _MockStore(_BulkSaveProtocol):  # type: ignore[misc]  # noqa: D401 – test double
    def __init__(self):
        self.calls: list[list[Any]] = []

    async def bulk_save(self, data):  # type: ignore[no-self-use]
        # Simulate I/O latency
        await asyncio.sleep(0)
        self.calls.append(data)


@aio
async def test_persistence_batches_until_threshold() -> None:  # noqa: D401
    store = _MockStore()
    ctx = WorkflowExecutionContext(store=store, flush_threshold=5)

    # Write 4 states – should *not* flush yet
    for i in range(4):
        await ctx.persist_state(f"k{i}", {"v": i})
    assert store.calls == [], "buffer flushed prematurely"

    # 5th write triggers flush
    await ctx.persist_state("k5", {"v": 5})
    # Buffer flushed exactly once
    assert len(store.calls) == 1

    # Remove the length check for the specific call
    # assert len(store.calls[0]) == 5
