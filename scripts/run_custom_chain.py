#!/usr/bin/env python
"""Demo: build & execute a ScriptChain with 3 different LLM providers and a web-search tool.

This script runs fully *offline*: we monkey-patch ``LLMService.generate`` so no
actual API calls are made.  It showcases:

1. Chain-of-thought prompting via the *reasoner* node (OpenAI provider).
2. Web search via ``WebSearchTool`` (tool node).
3. Summarisation using Anthropic provider.
4. Final answer refinement using Google Gemini provider.

Run:
    $ python scripts/run_custom_chain.py
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Tuple

from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig
from ice_orchestrator.workflow import ScriptChain
from ice_sdk.models.node_models import InputMapping, LLMOperatorConfig, SkillNodeConfig
from ice_sdk.providers.llm_service import LLMService  # noqa: E402
from ice_sdk.skills.web.search_skill import WebSearchSkill

# ---------------------------------------------------------------------------
# Helper – stub LLM responses so the demo runs offline
# ---------------------------------------------------------------------------


async def _generate_stub(
    self: LLMService,  # type: ignore[override]
    llm_config: LLMConfig,
    prompt: str,
    context: Dict[str, Any] | None = None,
    tools: List[Dict[str, Any]] | None = None,
    **_: Any,
) -> Tuple[str, Dict[str, int] | None, str | None]:
    """Return deterministic canned outputs based on *provider* for offline demo."""

    provider = (
        ModelProvider(llm_config.provider)
        if llm_config.provider
        else ModelProvider.OPENAI
    )

    if provider is ModelProvider.OPENAI:
        # Return a simple web search query
        return (
            "France capital city",
            {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            None,
        )

    if provider is ModelProvider.ANTHROPIC:
        # Summarise fake search results
        search_results = context.get("search_results", "") if context else ""
        return f"Summary: {search_results[:50]}...", None, None

    if provider is ModelProvider.GOOGLE:
        # Final answer
        summary = context.get("summary", "") if context else ""
        return f"Final answer based on summary -> {summary}", None, None

    return "", None, "Unsupported provider"


# Monkey-patch generate method once ------------------------------------------------
LLMService.generate = _generate_stub  # type: ignore[method-assign]

# ---------------------------------------------------------------------------
# Build nodes ----------------------------------------------------------------
# ---------------------------------------------------------------------------

reasoner_node = LLMOperatorConfig(
    id="reasoner",
    type="llm",
    name="Chain-of-Thought Reasoner",
    prompt=(
        "You are a knowledgeable assistant. Think step-by-step and craft a concise "
        "web search query that will help answer the user question.\n\n"
        "Question: {{question}}\n\n"
        "Thought (chain-of-thought):\n1."
    ),
    model="gpt-3.5-turbo",
    provider=ModelProvider.OPENAI,
    llm_config=LLMConfig(provider="openai", model="gpt-3.5-turbo"),
)

search_tool_node = SkillNodeConfig(
    id="web_search",
    type="skill",
    name="Web Search",
    tool_name=WebSearchSkill.name,
    tool_args={"query": "{search_query}"},  # placeholder – not used in stub
    dependencies=[reasoner_node.id],
    # Map input: search_query comes from reasoner output (raw string)
    input_mappings={
        "query": InputMapping(
            source_node_id=reasoner_node.id, source_output_key="output"
        )
    },
)

summary_node = LLMOperatorConfig(
    id="summariser",
    type="llm",
    name="Summariser",
    prompt="Summarise the following search results in one sentence:\n\n{{search_results}}",
    model="claude-3-haiku-20240307",
    provider=ModelProvider.ANTHROPIC,
    llm_config=LLMConfig(provider="anthropic", model="claude-3-haiku-20240307"),
    dependencies=[search_tool_node.id],
    input_mappings={
        "search_results": InputMapping(
            source_node_id=search_tool_node.id, source_output_key="results"
        )
    },
)

final_node = LLMOperatorConfig(
    id="refiner",
    type="llm",
    name="Answer Refiner",
    prompt="Use the summary to answer the original question clearly and concisely.\n\nSummary: {{summary}}",
    model="gemini-1.0-pro-latest",
    provider=ModelProvider.GOOGLE,
    llm_config=LLMConfig(provider="google", model="gemini-1.0-pro-latest"),
    dependencies=[summary_node.id],
    input_mappings={
        "summary": InputMapping(
            source_node_id=summary_node.id, source_output_key="output"
        )
    },
)

nodes = [reasoner_node, search_tool_node, summary_node, final_node]

# ---------------------------------------------------------------------------
# Build & execute chain ------------------------------------------------------
# ---------------------------------------------------------------------------


async def main() -> None:
    question = "What is the capital of France?"
    chain = ScriptChain(
        nodes=nodes,
        name="Demo Chain",
        initial_context={"question": question},
        tools=[WebSearchSkill()],
    )

    result = await chain.execute()
    print("\n=== Chain Execution Result ===")
    print("Success:", result.success)
    print("Output:", result.output)
    if result.error:
        print("Error:", result.error)


if __name__ == "__main__":
    # For demo purposes make sure network IO is not triggered
    os.environ.setdefault("SERPAPI_KEY", "stub-key")
    asyncio.run(main())
