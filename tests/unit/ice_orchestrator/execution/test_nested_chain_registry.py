import asyncio
import types

import pytest

from ice_sdk.registry.chain import global_chain_registry
from ice_orchestrator.execution.executors.builtin import nested_chain_executor
from ice_core.models.node_models import NestedChainConfig, NodeMetadata


class DummyChain:
    name = "dummy_chain"

    def __init__(self):
        self.context_manager = types.SimpleNamespace()

    async def execute(self):
        return types.SimpleNamespace(success=True, error=None, output={"msg": "ok"}, execution_time=0.0)


# Register dummy chain
_global_registered = False
if "dummy_chain" not in [n for n, _ in global_chain_registry]:
    global_chain_registry.register("dummy_chain", DummyChain())
    _global_registered = True


@pytest.mark.asyncio
async def test_nested_chain_executor_registry_lookup():
    cfg = NestedChainConfig(id="n1", type="nested_chain", chain="dummy_chain", input_schema={}, output_schema={})
    chain_stub = types.SimpleNamespace(context_manager=types.SimpleNamespace(execute_tool=lambda *a, **kw: None))
    ctx = {}
    res = await nested_chain_executor(chain_stub, cfg, ctx)
    assert res.success is True
    assert res.output == {"msg": "ok"} 