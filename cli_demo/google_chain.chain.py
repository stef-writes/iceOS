from src.ice_orchestrator.script_chain import ScriptChain
from src.ice_sdk.models.config import LLMConfig
from src.ice_sdk.models.node_models import AiNodeConfig, InputMapping, ToolNodeConfig

# Template Google Search tool node (we copy & override at runtime)
_google_search_node_template = ToolNodeConfig(
    id="web_search",
    name="Web Search (SerpAPI)",
    type="tool",
    tool_name="web_search",  # SerpAPI-backed implementation
    tool_args={
        # Placeholder – will be overridden in the constructor
        "query": "",
        # Optional parameters supported by WebSearchTool -----------------
        # "user_location": {"country": "US"},
        # "search_context_size": "medium",
    },
    dependencies=[],
)

# LLM summarization node
summarize_node = AiNodeConfig(
    id="summarize_results",
    name="Summarize Results",
    type="ai",
    model="deepseek-chat",
    prompt="Summarize these search results: {search_results}",
    llm_config=LLMConfig(provider="deepseek", model="deepseek-chat"),
    dependencies=["web_search"],
    input_mappings={
        "search_results": InputMapping(
            source_node_id="web_search",
            source_output_key="results",
        )
    },
)


class GoogleSearchDemoChain(ScriptChain):
    def __init__(self, user_inputs: dict | None = None):
        user_inputs = user_inputs or {}

        # Inject the user-provided query into a *fresh* copy of the template
        from copy import deepcopy

        google_search_node = deepcopy(_google_search_node_template)
        import os

        google_search_node.tool_args["query"] = user_inputs.get("search_query", "")
        # Inject API credentials (env vars take precedence over user inputs)
        google_search_node.tool_args["GOOGLE_API_KEY"] = os.getenv(
            "GOOGLE_API_KEY", user_inputs.get("GOOGLE_API_KEY", "")
        )
        google_search_node.tool_args["GOOGLE_CSE_ID"] = os.getenv(
            "GOOGLE_CSE_ID", user_inputs.get("GOOGLE_CSE_ID", "")
        )

        super().__init__(
            nodes=[google_search_node, summarize_node],
            name="google_search_demo",
            initial_context=user_inputs,
        )

        # ------------------------------------------------------------------
        # Register built-in Google search tool so *tool* nodes can execute it
        # ------------------------------------------------------------------
        try:
            # Register SerpAPI-backed web_search tool so *tool* nodes can execute it
            from src.ice_sdk.tools.hosted import WebSearchTool

            self.context_manager.register_tool(WebSearchTool())
        except ValueError:
            # Duplicate registration – safe to ignore when reloading in watch mode
            pass


# Factory helper so `ice run` can discover and instantiate the chain --------


def get_chain() -> GoogleSearchDemoChain:  # noqa: D401 – simple factory
    """Return a ready-to-run instance of *GoogleSearchDemoChain*.

    The search query can be provided via the ``SEARCH_QUERY`` environment
    variable.  If not set we fall back to a sensible default so running
    ``ice run cli_demo/google_chain.chain.py`` works out-of-the-box.
    """

    import os

    # Fallback ensures the demo still runs even without env var ----------
    query = os.getenv("SEARCH_QUERY", "ice sdk open source")
    return GoogleSearchDemoChain({"search_query": query})
