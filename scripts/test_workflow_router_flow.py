import asyncio
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from datetime import datetime
from typing import List

from app.agents import (
    AgentRegistry,
    NodeAgentAdapter,
    RouterAgent,
    WorkflowAgentAdapter,
)
from app.chains.orchestration.level_based_script_chain import LevelBasedScriptChain
from app.models.node_models import (
    AiNodeConfig,
    LLMConfig,
    ModelProvider,
    NodeConfig,
    NodeMetadata,
    ToolNodeConfig,
)
from app.nodes.factory import node_factory
from app.utils.context import GraphContextManager, SessionState

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
