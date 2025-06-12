"""Interactive test that spins up multiple agents and a workflow to validate
complex orchestration flows end-to-end.
"""
import asyncio
import os
import pathlib
import sys
from datetime import datetime

# Add src to import path so scripts work without installation
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from typing import List  # noqa: E402

from ice_agents import (  # noqa: E402
    AgentRegistry,
    NodeAgentAdapter,
    RouterAgent,
    WorkflowAgentAdapter,
)
from ice_orchestrator import LevelBasedScriptChain  # noqa: E402
from ice_sdk.models.config import LLMConfig, ModelProvider  # noqa: E402
from ice_sdk.models.node_models import (  # noqa: E402
    AiNodeConfig,
    InputMapping,
    NodeConfig,
    NodeMetadata,
    ToolNodeConfig,
)
from ice_orchestrator.nodes.factory import node_factory  # noqa: E402
from ice_sdk.context import GraphContextManager, SessionState  # noqa: E402

# Ensure ENV keys exist; warn user otherwise
for env_key in [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "DEEPSEEK_API_KEY",
]:
    if not os.getenv(env_key):
        print(
            f"⚠️  Environment variable {env_key} not set – corresponding LLM call may fail."
        )


def build_ai_node(
    node_id: str, provider: ModelProvider, model_name: str, prompt: str
) -> NodeConfig:
    llm_cfg = LLMConfig(provider=provider, model=model_name, temperature=0.2)
    return AiNodeConfig(
        id=node_id,
        type="ai",
        name=node_id,
        model=model_name,
        prompt=prompt,
        llm_config=llm_cfg,
        metadata=NodeMetadata(
            node_id=node_id, node_type="ai", created_at=datetime.utcnow()
        ),
    )


def build_tool_node(node_id: str, dep_id: str) -> NodeConfig:
    return ToolNodeConfig(
        id=node_id,
        type="tool",
        name=node_id,
        tool_name="word_count",
        tool_args={},
        dependencies=[dep_id],
        input_mappings={
            "text": InputMapping(source_node_id=dep_id, source_output_key=".")
        },
        metadata=NodeMetadata(
            node_id=node_id, node_type="tool", created_at=datetime.utcnow()
        ),
    )


async def main():
    # ------------------------------------------------------------------
    # 1. Build nodes ----------------------------------------------------
    # ------------------------------------------------------------------
    nodes: List[NodeConfig] = [
        build_ai_node(
            "openai_node",
            ModelProvider.OPENAI,
            "gpt-3.5-turbo",
            "Reply with the input text unchanged.",
        ),
        build_ai_node(
            "anthropic_node",
            ModelProvider.ANTHROPIC,
            "claude-3-haiku-20240307",
            "Summarize the input in one sentence.",
        ),
        build_ai_node(
            "google_node",
            ModelProvider.GOOGLE,
            "gemini-1.0-pro-latest",
            "Translate the text to French.",
        ),
        build_ai_node(
            "deepseek_node",
            ModelProvider.DEEPSEEK,
            "deepseek-chat",
            "List the unique words in the text.",
        ),
        build_tool_node("tool1", "openai_node"),
        build_tool_node("tool2", "anthropic_node"),
        build_tool_node("tool3", "google_node"),
    ]

    graph_ctx = GraphContextManager()
    chain = LevelBasedScriptChain(
        nodes, name="seven_node_flow", context_manager=graph_ctx
    )

    workflow_agent = WorkflowAgentAdapter(
        chain, name="seven_node_workflow", description="Demo workflow with 7 nodes"
    )

    # Standalone agents
    openai_node_agent = NodeAgentAdapter(
        node_factory(
            nodes[0], context_manager=graph_ctx, llm_config=nodes[0].llm_config
        ),
        name="openai_agent",
    )
    tool_agent = NodeAgentAdapter(
        node_factory(
            build_tool_node("single_tool", "openai_node"), context_manager=graph_ctx
        ),
        name="single_tool_agent",
    )

    # Registry ----------------------------------------------------------
    registry = AgentRegistry()
    registry.register(workflow_agent)
    registry.register(openai_node_agent)
    registry.register(tool_agent)

    # Router ------------------------------------------------------------
    router = RouterAgent(registry)

    session = SessionState("complex-session")

    user_input = {
        "text": "This is a complex system test sentence for our agent framework."
    }

    result = await router.execute(session, user_input)

    print("Success:", result.success)
    print("Output:", result.output)
    print("Session outputs keys:", session.last_outputs.keys())


if __name__ == "__main__":
    asyncio.run(main())
