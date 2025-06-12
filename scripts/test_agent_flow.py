import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import asyncio
from datetime import datetime

from ice_agents import AgentRegistry, NodeAgentAdapter
from ice_sdk.models.node_models import NodeMetadata, ToolNodeConfig
from ice_orchestrator.nodes.factory import node_factory
from ice_sdk.context import (  # GraphContextManager already exists
    GraphContextManager,
    SessionState,
)


def build_word_count_agent():
    # ------------------------------------------------------------------
    # 1. Create node config ------------------------------------------------
    # ------------------------------------------------------------------
    cfg = ToolNodeConfig(
        id="word_count_node",
        type="tool",
        name="Word Count",
        tool_name="word_count",  # built-in tool in app.tools.builtins.word_count
        tool_args={},
        metadata=NodeMetadata(
            node_id="word_count_node",
            node_type="tool",
            name="Word Count Node",
            description="Counts words in a given text",
            created_at=datetime.utcnow(),
        ),
    )

    # ------------------------------------------------------------------
    # 2. Instantiate concrete node ----------------------------------------
    # ------------------------------------------------------------------
    context_mgr = GraphContextManager()
    node = node_factory(cfg, context_manager=context_mgr)

    # ------------------------------------------------------------------
    # 3. Wrap as agent -----------------------------------------------------
    # ------------------------------------------------------------------
    return NodeAgentAdapter(node, name="word_counter", description="Counts words")


async def main():
    # Session -------------------------------------------------------------
    session = SessionState("demo-session")

    # Registry ------------------------------------------------------------
    registry = AgentRegistry()
    agent = build_word_count_agent()
    registry.register(agent)

    # Execute -------------------------------------------------------------
    text = "Hello world from our new agent framework!"
    result = await registry.get("word_counter").execute(session, {"text": text})
    print("Agent success: ", result.success)
    print("Agent output : ", result.output)
    print("Session memory: ", session.last_outputs)


if __name__ == "__main__":
    asyncio.run(main())
