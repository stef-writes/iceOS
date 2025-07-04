"""Demo *Essay Writer* ScriptChain showcasing multiple thoughtful nodes.

The flow:
    1. **generate_query** – AI node turns *topic* → detailed search query.
    2. **web_search** – Tool node (SerpAPI) executes Google search.
    3. **summarize_results** – AI node provides a concise summary of raw search engine results before fact extraction.
    4. **extract_key_points** – AI node extracts salient facts.
    5. **build_outline** – AI node converts key points → outline.
    6. **language_styler** – Tool node rewrites outline in requested style.
    7. **keyword_density** – Tool node analyses keyword density.

All nodes follow repo guidelines (type-hints, Pydantic models, async I/O).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.models.node_models import AiNodeConfig, InputMapping, ToolNodeConfig
from ice_sdk.tools.builtins.essay_tools import (
    KeywordDensityTool,
    LanguageStyleAdapterTool,
)
from ice_sdk.tools.hosted import WebSearchTool

# ---------------------------------------------------------------------------
#  Node definitions ----------------------------------------------------------
# ---------------------------------------------------------------------------
# 1. Generate detailed search query -----------------------------------------
_generate_query_node = AiNodeConfig(
    id="generate_query",
    name="Generate Search Query",
    type="ai",
    model="deepseek-chat",
    provider=ModelProvider.DEEPSEEK,
    prompt=(
        "Given the essay topic '{topic}', craft a detailed web search query that will surface high-quality, authoritative sources.\n"
        'Respond with a PLAIN JSON object (no markdown, no code fences) matching this schema: {\\"query\\": \\"...\\"}'
    ),
    llm_config=LLMConfig(
        provider=ModelProvider.DEEPSEEK,
        model="deepseek-chat",
        temperature=0.3,
        max_tokens=512,
        top_p=0.9,
        # 'system_message' stored via custom_parameters for lint safety
        custom_parameters={
            "system_message": (
                "You are a research librarian specializing in academic writing. "
                "Generate queries that prioritize authoritative (.edu, .gov) sources "
                "and recent publications."
            )
        },
    ),
    input_schema={"topic": str},
    output_schema={"query": str},
    timeout_seconds=20,
    retries=2,
)

# 1.b Topic decomposition ----------------------------------------------------
_topic_mapper_node = AiNodeConfig(
    id="topic_mapper",
    name="Topic Decomposer",
    type="ai",
    model="gpt-4o",
    provider=ModelProvider.OPENAI,
    prompt=(
        "Decompose the essay topic into 3–7 research sub-questions covering what, why, impact, "
        'controversy, and future outlook. Respond with a PLAIN JSON object matching this schema: {\\"sub_questions\\": [\\"...\\"]}. Topic: {topic}'
    ),
    llm_config=LLMConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-4o",
        temperature=0.2,
        max_tokens=256,
        top_p=0.9,
    ),
    input_schema={"topic": str},
    output_schema={"sub_questions": list},
    dependencies=["generate_query"],
    input_mappings={
        "topic": InputMapping(
            source_node_id="generate_query",
            source_output_key="query",
        )
    },
)

# 2. Web search tool node ----------------------------------------------------
_web_search_template = ToolNodeConfig(
    id="web_search",
    name="Web Search (SerpAPI)",
    type="tool",
    tool_name="web_search",
    tool_args={"query": "{query}", "num_results": 10},  # ctx placeholder
    dependencies=["generate_query"],
    input_mappings={
        "query": InputMapping(
            source_node_id="generate_query",
            source_output_key="query",
        )
    },
    input_schema={"query": str},
    output_schema={"results": list},
    timeout_seconds=30,
    retries=1,
)

# 3. Summarize search results ------------------------------------------------
_summarize_results_node = AiNodeConfig(
    id="summarize_results",
    name="Summarize Search Results",
    type="ai",
    model="gpt-4o",
    provider=ModelProvider.OPENAI,
    prompt=(
        "Summarize these search results in 5 bullet points: {search_results}.\n"
        'Return a PLAIN JSON object, no markdown, with key \'summary_points\', e.g. {\\"summary_points\\": [\\"point1\\", ...]}'
    ),
    llm_config=LLMConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-4o",
        temperature=0.25,
        max_tokens=512,
        top_p=0.9,
        custom_parameters={
            "system_message": (
                "You are an analyst summarizing web search snippets into crisp, neutral takeaways."
            )
        },
    ),
    dependencies=["web_search"],
    input_mappings={
        "search_results": InputMapping(
            source_node_id="web_search",
            source_output_key="results",
        )
    },
    input_schema={"search_results": list},
    output_schema={"summary_points": list},
    timeout_seconds=25,
    retries=2,
)

# 4. Extract key points ------------------------------------------------------
_extract_points_node = AiNodeConfig(
    id="extract_key_points",
    name="Extract Key Points",
    type="ai",
    model="claude-3-haiku-20240307",
    provider=ModelProvider.ANTHROPIC,
    prompt=(
        "From these search results: {search_results}\n"
        'Extract the 7 most important facts or data points. Return PLAIN JSON (no markdown) in the form {\\"key_points\\": [\\"point1\\", ...]}'
    ),
    llm_config=LLMConfig(
        provider=ModelProvider.ANTHROPIC,
        model="claude-3-haiku-20240307",
        temperature=0.2,
        max_tokens=1024,
        top_p=0.85,
        custom_parameters={
            "system_message": (
                "You are a fact extraction expert. Ignore opinionated content and "
                "focus on verifiable claims only."
            )
        },
    ),
    dependencies=["web_search"],
    input_mappings={
        "search_results": InputMapping(
            source_node_id="web_search",
            source_output_key="results",
        )
    },
    input_schema={"search_results": list},
    output_schema={"key_points": list},
    timeout_seconds=30,
    retries=2,
)

# 5. Build outline -----------------------------------------------------------
_outline_node = AiNodeConfig(
    id="build_outline",
    name="Build Outline",
    type="ai",
    model="gpt-4o",
    provider=ModelProvider.OPENAI,
    prompt=(
        "Using the following key points:\n{key_points}\n\n"
        "Draft a detailed, hierarchical essay outline (e.g. I., II., III. with sub-levels A., 1., a.).\n\n"
        "You MUST respond with *valid JSON only* – no markdown, no code fences, no additional keys.\n"
        "Format:\n"
        '{"outline": "I. Introduction\\n   A. Background\\n   B. Thesis\\nII. Key Point 1\\n   A. Supporting detail"}'
    ),
    llm_config=LLMConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-4o",
        temperature=0.4,
        max_tokens=2048,
        top_p=0.95,
        custom_parameters={
            "system_message": (
                "You are an academic writing assistant. "
                "Create structured outlines using standard I.A.1.a hierarchy."
            )
        },
    ),
    dependencies=["extract_key_points"],
    input_mappings={
        "key_points": InputMapping(
            source_node_id="extract_key_points",
            source_output_key="key_points",
        )
    },
    input_schema={"key_points": list},
    output_schema={"outline": str},
    timeout_seconds=45,
    retries=2,
)

# 5.b Outline critic ---------------------------------------------------------
_outline_reviewer = AiNodeConfig(
    id="outline_critic",
    name="Outline Critic",
    type="ai",
    model="gpt-4o",
    provider=ModelProvider.OPENAI,
    prompt=(
        "You are a meticulous academic peer reviewer. Analyse the outline below for gaps, logical "
        "flaws, redundancy, or imbalance. Respond in JSON with keys 'weaknesses', 'missing_sections', "
        "and 'score' (0-10). Outline:\n{outline}"
    ),
    llm_config=LLMConfig(
        provider=ModelProvider.OPENAI, model="gpt-4o", temperature=0.0
    ),
    dependencies=["build_outline"],
    input_mappings={
        "outline": InputMapping(
            source_node_id="build_outline",
            source_output_key="outline",
        )
    },
    output_schema={
        "weaknesses": list,
        "missing_sections": list,
        "score": float,
    },
)

# 5.c Outline refiner --------------------------------------------------------
_outline_refiner = AiNodeConfig(
    id="outline_refiner",
    name="Outline Refiner",
    type="ai",
    model="gpt-4o",
    provider=ModelProvider.OPENAI,
    prompt=(
        "Original outline:\n{outline}\n\nCritique:\n{critique}\n\nProduce an improved outline that addresses all weaknesses and missing sections."
    ),
    llm_config=LLMConfig(
        provider=ModelProvider.OPENAI, model="gpt-4o", temperature=0.6
    ),
    dependencies=["outline_critic", "build_outline"],
    input_mappings={
        "outline": InputMapping(
            source_node_id="build_outline",
            source_output_key="outline",
        ),
        "critique": InputMapping(
            source_node_id="outline_critic",
            source_output_key="weaknesses",
        ),
    },
    output_schema={"refined_outline": str},
    retries=1,
)

# 6.b Diagram drafter --------------------------------------------------------
_diagram_drafter = AiNodeConfig(
    id="diagram_drafter",
    name="Diagram Drafter",
    type="ai",
    model="deepseek-chat",
    provider=ModelProvider.DEEPSEEK,
    prompt=(
        "Convert the following outline into Mermaid 'graph TD' code representing the logical flow:\n{outline}"
    ),
    llm_config=LLMConfig(
        provider=ModelProvider.DEEPSEEK, model="deepseek-chat", temperature=0.3
    ),
    dependencies=["outline_refiner"],
    input_mappings={
        "outline": InputMapping(
            source_node_id="outline_refiner",
            source_output_key="refined_outline",
        )
    },
    output_schema={"mermaid_code": str},
)

# 6. Language styler tool node ----------------------------------------------
_language_style_node = ToolNodeConfig(
    id="language_styler",
    name="Style Outline",
    type="tool",
    tool_name="language_style_adapter",
    tool_args={
        "text": "{outline}",  # placeholder filled from ctx
        "style": "academic",  # default value, can be overridden later
        "reading_level": "college",
    },
    dependencies=["build_outline"],
    input_mappings={
        "outline": InputMapping(
            source_node_id="build_outline",
            source_output_key="outline",
        ),
    },
    input_schema={
        "outline": str,
        "style": str,
    },
    output_schema={"styled_text": str},
    timeout_seconds=20,
    retries=1,
)

# 7. Keyword density analyzer -----------------------------------------------
_keyword_density_node = ToolNodeConfig(
    id="keyword_density",
    name="Keyword Density Analyzer",
    type="tool",
    tool_name="keyword_analyzer",
    tool_args={
        "text": "{styled_text}",
        "keywords": ["AI", "framework"],
        "min_keyword_length": 3,
    },
    dependencies=["language_styler"],
    input_mappings={
        "styled_text": InputMapping(
            source_node_id="language_styler",
            source_output_key="styled_text",
        )
    },
    input_schema={
        "styled_text": str,
        "keywords": list,
    },
    output_schema={
        "density": dict,
        "total_words": int,
        "highlighted_html": str,
    },
    timeout_seconds=15,
    retries=1,
)


class EssayWriterChain(ScriptChain):
    """Concrete ScriptChain implementing the enhanced demo."""

    def __init__(self, user_inputs: Dict[str, Any] | None = None):  # noqa: ANN401
        user_inputs = user_inputs or {}

        # ------------------------------------------------------------------
        # Instantiate nodes (deepcopy works around shared mutable defaults) --
        # ------------------------------------------------------------------
        web_search_node = deepcopy(_web_search_template)
        # If the user supplies explicit topic → bypass query generation
        if "search_query" in user_inputs:
            web_search_node.tool_args["query"] = user_inputs["search_query"]
            # Also skip dependency mapping in that case ------------------
            web_search_node.input_mappings = {}
            web_search_node.dependencies = []

        # Insert user-defined style / keywords when provided ---------------
        language_style_node = deepcopy(_language_style_node)
        if "style" in user_inputs:
            language_style_node.tool_args["style"] = user_inputs["style"]
        keyword_node = deepcopy(_keyword_density_node)
        if "keywords" in user_inputs and isinstance(user_inputs["keywords"], list):
            keyword_node.tool_args["keywords"] = user_inputs["keywords"]

        # ------------------------------------------------------------------
        node_configs = [
            _generate_query_node,
            _topic_mapper_node,
            web_search_node,
            _summarize_results_node,
            _extract_points_node,
            _outline_node,
            _outline_reviewer,
            _outline_refiner,
            _diagram_drafter,
            language_style_node,
            keyword_node,
        ]

        super().__init__(
            nodes=node_configs,
            name="essay_writer_demo",
            initial_context=user_inputs,
        )

        # Register custom tools so *tool* nodes can execute them -----------
        for tool_cls in (LanguageStyleAdapterTool, KeywordDensityTool):
            try:
                self.context_manager.register_tool(tool_cls())
            except ValueError:
                continue
        # Also ensure web search tool is registered -----------------------
        try:
            self.context_manager.register_tool(WebSearchTool())
        except ValueError:
            pass


# Factory helper -------------------------------------------------------------


def get_chain() -> EssayWriterChain:  # noqa: D401 – simple factory
    """Return a ready-to-run *EssayWriterChain* instance.

    Environment variables can override defaults:
      • TOPIC – essay topic (default: "impact of artificial intelligence")
      • STYLE – writing style (default: "academic")
    """

    import os

    topic = os.getenv("TOPIC", "impact of artificial intelligence")
    style = os.getenv("STYLE", "academic")
    keywords_env = os.getenv("KEYWORDS")
    kw_list = keywords_env.split(",") if keywords_env else ["AI", "impact"]

    return EssayWriterChain({"topic": topic, "style": style, "keywords": kw_list})
