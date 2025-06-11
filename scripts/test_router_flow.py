import asyncio
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from datetime import datetime

from app.agents import AgentRegistry, NodeAgentAdapter, RouterAgent
from app.models.node_models import NodeMetadata, ToolNodeConfig
from app.nodes.factory import node_factory
from app.utils.context import GraphContextManager, SessionState


def build_word_count_agent():
    cfg = ToolNodeConfig(
        id="word_count_node",
        type="tool",
        name="Word Count",
        tool_name="word_count",
        tool_args={},
        metadata=NodeMetadata(
            node_id="word_count_node",
            node_type="tool",
            name="Word Count Node",
            description="Counts words in a given text",
            created_at=datetime.utcnow(),
        ),
    )
    node = node_factory(cfg, context_manager=GraphContextManager())
    return NodeAgentAdapter(node, name="word_counter", description="Counts words")


async def main():
    session = SessionState("router-session")
    registry = AgentRegistry()
    registry.register(build_word_count_agent())

    router = RouterAgent(registry)

    # User request
    text = "Could you tell me how many words are in this sentence?"
    res = await router.execute(session, {"text": text})

    print("Router result success:", res.success)
    print("Output:", res.output)
    print("Session memory:", session.last_outputs)


if __name__ == "__main__":
    asyncio.run(main())
