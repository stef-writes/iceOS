#!/usr/bin/env python3
"""micro_reasoning_chain.py – showcase intertwined nodes + registry agent

This script demonstrates how to:
1. Register a custom **AgentNode** (``research_agent``) that can invoke
   existing tools (``web_search``).
2. Expose that agent as a *tool* so other workflow nodes can call it.
3. Build a 4-node ScriptChain where outputs flow between nodes via
   ``input_mappings``.
4. Execute the chain end-to-end without touching the HTTP MCP API.

Run the example:
    $ python create_reasoning_chain.py

The chain topology
──────────────────
    [analyze]  ──▶  [research]  ──▶  [check_research]  ──▶  [synthesise]
                   (agent tool)        (condition)

• **analyze** (AI node) analyses the incoming *question*.
• **research** (Tool node) calls *research_agent_tool* which internally
  uses the built-in ``web_search`` tool.
• **check_research** (Condition node) ensures the research summary is
  non-empty before letting execution continue.
• **synthesise** (AI node) merges both analysis and research results into
  a concise answer.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict

from ice_sdk.agents.agent_node import AgentNode
from ice_sdk.context import GraphContextManager
from ice_sdk.models.agent_models import AgentConfig, ModelSettings
from ice_sdk.models.node_models import InputMapping
from ice_sdk.tools.web.search_tool import WebSearchTool
from iceos import Chain, Node

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def build_chain(ctx_mgr: GraphContextManager):  # noqa: D401 – helper name
    """Return a fully-wired ScriptChain instance."""

    # ------------------------------------------------------------------
    # 1. Create & register a *research_agent* that can call WebSearchTool
    # ------------------------------------------------------------------
    web_search_tool = WebSearchTool()

    agent_cfg = AgentConfig(
        name="research_agent",
        instructions=(
            "You are an internet research assistant. When given a JSON input "
            "containing a 'query' field, call the 'web_search' tool exactly "
            'once and then return a JSON object {"summary": <concise-summary>} '
            "without additional commentary."
        ),
        model="gpt-4",
        model_settings=ModelSettings(model="gpt-4"),
        tools=[web_search_tool],
    )

    research_agent = AgentNode(config=agent_cfg, context_manager=ctx_mgr)

    # Wrap the agent so workflow nodes can *invoke* it like any other tool.
    research_tool = research_agent.as_tool(
        name="research_agent_tool",
        description="Fetches live information and returns a short summary.",
    )

    # Register agent & its tool with the shared context manager.
    ctx_mgr.register_agent(research_agent)
    ctx_mgr.register_tool(research_tool)

    # ------------------------------------------------------------------
    # 2. Build the Chain using the ergonomic *iceos* builders
    # ------------------------------------------------------------------
    chain_builder = (
        Chain("Micro Reasoning Module")
        # --- Node 1: initial analysis ----------------------------------
        .add_node(
            Node.ai("analyze")
            .prompt(
                "Analyze the following question in depth: What are the latest advancements in quantum computing?"
            )
            .model("gpt-4")
        )
        # --- Node 2: call the *research_agent_tool* --------------------
        .add_node(
            Node.tool("research")
            .tool_name(research_tool.name)
            # *input* argument will be filled via ctx mapping below --------
            .tool_args(input={"query": "{analyze_output}"})
            .depends_on("analyze")
        )
        # --- Node 3: guard – make sure we actually got a summary --------
        .add_node(
            Node.condition("check_research")
            .expression("research_output.get('summary', '') != ''")
            .depends_on("research")
        )
        # --- Node 4: final synthesis -----------------------------------
        .add_node(
            Node.ai("synthesise")
            .prompt(
                "Using the analysis below\n\n"
                "ANALYSIS:\n{{analyze_output}}\n\n"
                "and the research summary:\n{{research_output}}\n\n"
                "Write a concise, well-structured answer."
            )
            .model("gpt-4")
            .depends_on("check_research")
        )
    )

    # Build ScriptChain and attach input mappings ----------------------
    sc = chain_builder.build()
    nodes: Dict[str, object] = sc.nodes  # type: ignore[assignment]

    # Map downstream placeholders to upstream outputs ------------------
    nodes["research"].input_mappings = {
        "analyze_output": InputMapping(
            source_node_id="analyze",
            source_output_key=".",  # entire output object/text
        )
    }
    nodes["check_research"].input_mappings = {
        "research_output": InputMapping(
            source_node_id="research", source_output_key="."
        )
    }
    nodes["synthesise"].input_mappings = {
        "analyze_output": InputMapping(source_node_id="analyze", source_output_key="."),
        "research_output": InputMapping(
            source_node_id="research", source_output_key="."
        ),
    }

    # Plug in the shared context manager so all agents/tools see the same registry
    sc.context_manager = ctx_mgr
    return sc


async def main() -> None:  # noqa: D401 – script entry-point
    """Run the micro-reasoning chain once with a sample *question*."""

    ctx_mgr = GraphContextManager()

    # Pre-seed session context with the *question* so {{question}} resolves.
    ctx = ctx_mgr.get_context(session_id="demo")
    if ctx is None:
        ctx = ctx_mgr.get_context(session_id="demo")  # create lazily
    ctx.metadata["question"] = "What are the latest advancements in quantum computing?"

    chain = await build_chain(ctx_mgr)
    result = await chain.execute()

    print("\n=== Chain finished ===")
    print("success :", result.success)
    if result.error:
        print("error   :", result.error)
    print("output  :", result.output)


if __name__ == "__main__":
    asyncio.run(main())
