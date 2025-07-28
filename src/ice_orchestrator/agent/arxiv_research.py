from __future__ import annotations

"""ArxivResearchAgent – minimal research agent that leverages the built-in
``arxiv_search`` tool, local memory, and an LLM summarisation loop.

The agent:
1. Receives a *topic* string.
2. Calls ``arxiv_search`` (max 5 results) to retrieve fresh papers.
3. Iterates over each paper, asking the LLM service for a 3-bullet summary.
4. Returns the aggregated bullet list and stores a snapshot in memory.

This demonstrates:
• Tool usage inside an Agent node
• Looping logic (one LLM call per paper)
• UnifiedMemory read/write
"""

from typing import Any, Dict, List
from datetime import datetime

from ice_core.unified_registry import registry, global_agent_registry
from ice_sdk.services import ServiceLocator
from ice_sdk.utils.errors import ToolExecutionError

from .memory import MemoryAgent, MemoryAgentConfig


class ArxivResearchAgentConfig(MemoryAgentConfig):
    """Config class that fixes *tools* whitelist and sane defaults."""

    tools: List[str] = ["arxiv_search"]  # only tool we allow for now
    agent_config: Dict[str, Any] = {
        "system_prompt": (
            "You are ArxivResearcher, an expert scientific assistant. "
            "For each provided paper you must write 3 crisp bullet points (max 25 words each) "
            "highlighting the main contribution, methods, and significance."
        ),
        "max_retries": 3,
    }


class ArxivResearchAgent(MemoryAgent):
    """Agent that researches a topic on *arXiv* and summarises the findings."""

    config: ArxivResearchAgentConfig

    async def _execute_with_memory(self, enhanced_inputs: Dict[str, Any]) -> Dict[str, Any]:
        topic: str = enhanced_inputs.get("topic") or enhanced_inputs.get("query", "").strip()
        if not topic:
            raise ValueError("'topic' input is required")

        max_results: int = int(enhanced_inputs.get("max_results", 5))
        max_results = max(1, min(max_results, 10))  # safety bounds

        # -----------------------------
        # 1. Search arXiv -------------
        # -----------------------------
        arxiv_tool = registry.get_tool("arxiv_search")
        if not arxiv_tool:
            raise ToolExecutionError("arxiv_search", "Tool not registered")

        search_result = await arxiv_tool.execute(query=topic, max_results=max_results)
        papers: List[Dict[str, str]] = search_result.get("papers", [])
        if not papers:
            return {"status": "no_results", "topic": topic}

        # -----------------------------
        # 2. Summarise each paper -----
        # -----------------------------
        llm_service = ServiceLocator.get("llm_service")
        summaries: List[Dict[str, str]] = []
        for idx, paper in enumerate(papers, 1):
            prompt = (
                f"Paper {idx}/{len(papers)} – summarise in 3 bullet points (<=25 words each).\n"
                f"Title: {paper['title']}\n"
                f"Abstract: {paper['summary']}"
            )
            llm_resp = await llm_service.complete(prompt=prompt, config=self.config.llm_config)
            summaries.append({
                "title": paper["title"],
                "summary": llm_resp.get("text", "")
            })

        # -----------------------------
        # 3. Persist to memory --------
        # -----------------------------
        if self.memory:
            await self.memory.remember_fact(
                fact=f"arxiv_research:{topic}:{datetime.utcnow().isoformat()}",
                metadata={"papers": papers, "summaries": summaries},
            )

        # -----------------------------
        # 4. Aggregate final answer ---
        # -----------------------------
        final_answer = "\n\n".join(
            f"{item['title']}\n{item['summary']}" for item in summaries
        )

        return {
            "status": "success",
            "topic": topic,
            "papers": papers,
            "summaries": summaries,
            "response": final_answer,
        }


# ---------------------------------------------------------------------------
# Registration (import-side effect) -----------------------------------------
# ---------------------------------------------------------------------------

global_agent_registry.register_agent(
    "arxiv_researcher", "ice_orchestrator.agent.arxiv_research.ArxivResearchAgent"
) 