import asyncio
import uuid

import pytest

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.node_models import ToolNodeConfig
from ice_sdk.tools.builtins.deterministic import SleepTool


@pytest.mark.timeout(30)
@pytest.mark.asyncio
async def test_chain_handles_parallel_invocations() -> None:
    """Execute 200 trivial chains in parallel to flush out race conditions."""

    # Build trivial chain template -----------------------------------
    def _make_chain() -> ScriptChain:
        node = ToolNodeConfig(
            id=str(uuid.uuid4()),
            type="tool",
            name="sleep",
            tool_name="sleep",
            tool_args={"seconds": 0.01},
        )
        return ScriptChain(nodes=[node], tools=[SleepTool()])

    chains = [_make_chain() for _ in range(200)]

    results = await asyncio.gather(*(chain.execute() for chain in chains))

    assert all(r.success for r in results) 