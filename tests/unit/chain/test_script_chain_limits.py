# pyright: reportGeneralTypeIssues=false
import pytest

from ice_orchestrator.workflow import ScriptChain
from ice_sdk.context import GraphContextManager
from ice_sdk.context.manager import GraphContext
from ice_sdk.models.node_models import SkillNodeConfig
from ice_sdk.skills.service import ToolService
from ice_sdk.skills.system.sum_skill import SumSkill


@pytest.mark.asyncio
async def test_depth_ceiling_stops_execution():
    ts = ToolService()
    ts.register(SumSkill)  # already registered but safe

    # Build 3-level linear chain with dummy tool nodes
    nodes = [  # type: ignore[var-annotated]
        SkillNodeConfig(
            id=f"n{i}",
            name=f"node{i}",
            type="tool",
            tool_name="sum",
            tool_args={"numbers": [i]},
        )
        for i in range(3)
    ]
    # establish dependencies
    nodes[1].dependencies = ["n0"]
    nodes[1].level = 1
    nodes[2].dependencies = ["n1"]
    nodes[2].level = 2

    ctx_mgr = GraphContextManager()
    ctx_mgr.set_context(GraphContext(session_id="test"))
    chain = ScriptChain(  # type: ignore[arg-type]
        nodes=nodes,
        name="depth-test",
        token_ceiling=None,
        depth_ceiling=2,
        tools=[SumSkill()],
        context_manager=ctx_mgr,
    )
    result = await chain.execute()
    assert not result.success
    assert "Depth ceiling" in (result.error or "")
