"""Router scenario combining a simple workflow agent with individual node agents."""
import asyncio
import pathlib
import sys
from datetime import datetime

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from typing import List  # noqa: E402

from ice_agents import (  # noqa: E402
    AgentRegistry,
    NodeAgentAdapter,
    RouterAgent,
    WorkflowAgentAdapter,
)
from ice_orchestrator import LevelBasedScriptChain  # noqa: E402
from ice_sdk.models.node_models import (  # noqa: E402
    NodeConfig,
    NodeMetadata,
    ToolNodeConfig,
)
from ice_orchestrator.nodes.factory import node_factory  # noqa: E402
from ice_sdk.context import GraphContextManager, SessionState  # noqa: E402

# ----------------------------------------------------------------------
# Build a tiny workflow: Node1 (word_count tool) ➜ Node2 (word_count tool on_phrase)
# ----------------------------------------------------------------------


def build_tool_node(node_id: str) -> NodeConfig:
    return ToolNodeConfig(
        id=node_id,
        type="tool",
        name=node_id,
        tool_name="word_count",
        tool_args={},
        metadata=NodeMetadata(
            node_id=node_id,
            node_type="tool",
            created_at=datetime.utcnow(),
        ),
    )


def build_workflow() -> WorkflowAgentAdapter:
    nodes: List[NodeConfig] = [build_tool_node("count1"), build_tool_node("count2")]
    chain = LevelBasedScriptChain(
        nodes, name="double_count", context_manager=GraphContextManager()
    )
    return WorkflowAgentAdapter(
        chain, name="double_counter", description="Counts words twice"
    )


async def main():
    session = SessionState("workflow-session")
    registry = AgentRegistry()

    # Single leaf agent + workflow agent
    registry.register(build_workflow())
    # Also register simple node agent for variety
    single_node_agent = NodeAgentAdapter(
        node_factory(
            build_tool_node("count_single"), context_manager=GraphContextManager()
        ),
        name="single_counter",
    )
    registry.register(single_node_agent)

    router = RouterAgent(registry)

    res = await router.execute(session, {"text": "Router should decide how many words"})
    print("Router chose success:", res.success)
    print("Output:", res.output)
    print("Session memory keys:", session.last_outputs.keys())


if __name__ == "__main__":
    asyncio.run(main())
