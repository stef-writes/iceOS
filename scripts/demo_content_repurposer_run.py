import asyncio
import sys
from uuid import uuid4

from ice_orchestrator import ScriptChain
from ice_sdk.context.manager import GraphContextManager
from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig, InputMapping
from ice_sdk.tools.base import BaseTool, ToolError

# ---------------------------------------------------------------------------
# 1. CLI arg – YouTube URL ---------------------------------------------------
# ---------------------------------------------------------------------------

def main() -> None:  # noqa: D401
    if len(sys.argv) < 2:
        print("Usage: python demo_content_repurposer_run.py <youtube_url>")
        sys.exit(1)
    youtube_url = sys.argv[1]

    # ----------------------------------------------------------------------
    # 2. Stub LLM provider – no external calls -----------------------------
    # ----------------------------------------------------------------------
    from ice_sdk.providers.llm_service import LLMService

    async def _mock_generate(self, *_, **__):  # type: ignore[reportFunctionMemberAccess]
        """Return deterministic text without network IO."""
        return (
            "dummy text",  # generated text
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            None,
        )

    # Monkey-patch *all* instances.
    LLMService.generate = _mock_generate  # type: ignore[method-assign]

    # ----------------------------------------------------------------------
    # 3. Stub network-centric tools ----------------------------------------
    # ----------------------------------------------------------------------
    class StubHttpTool(BaseTool):
        name = "http_request"
        description = "Stubbed HTTP request"
        parameters_schema = {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
            },
            "required": ["url"],
        }

        async def run(self, **kwargs):  # type: ignore[override]
            return {
                "status_code": 200,
                "body": "{\"transcript\": \"lorem ipsum dolor sit amet ...\"}",
                "headers": {},
            }

    class StubWebSearchTool(BaseTool):
        name = "web_search"
        description = "Stubbed web search"
        parameters_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        }

        async def run(self, **kwargs):  # type: ignore[override]
            return {"results": [
                {"title": "Top Hashtags", "url": "https://example.com", "snippet": "#ai #python"}
            ]}

    # ----------------------------------------------------------------------
    # 4. Build node configurations ----------------------------------------
    # ----------------------------------------------------------------------
    llm_cfg = LLMConfig(provider=ModelProvider.OPENAI, model="gpt-3.5-turbo", temperature=0.0)

    nodes = []

    # parse_url -----------------------------------------------------------
    nodes.append(
        AiNodeConfig(
            id="parse_url",
            type="ai",
            name="Parse URL",
            model="gpt-3.5-turbo",
            prompt="Extract video_id, title and channel from the YouTube URL in JSON.",
            llm_config=llm_cfg,
            input_mappings={"youtube_url": youtube_url},  # type: ignore[arg-type]
            output_schema={"video_id": "str", "title": "str", "channel": "str"},
        )
    )

    # fetch_transcript (tool) --------------------------------------------
    nodes.append(
        ToolNodeConfig(
            id="fetch_transcript",
            type="tool",
            name="Fetch Transcript",
            tool_name="http_request",
            tool_args={
                "method": "GET",
                "url": "https://youtubetranscript.com/?video_id={video_id}",
            },
            dependencies=["parse_url"],
            input_mappings={
                "video_id": InputMapping(source_node_id="parse_url", source_output_key="video_id")
            },
        )
    )

    # summarise_video ----------------------------------------------------
    nodes.append(
        AiNodeConfig(
            id="summarise_video",
            type="ai",
            name="Summarise Video",
            model="gpt-3.5-turbo",
            prompt="Provide a concise summary of the transcript.",
            llm_config=llm_cfg,
            dependencies=["fetch_transcript"],
            input_mappings={
                "transcript": InputMapping(source_node_id="fetch_transcript", source_output_key="body")
            },
        )
    )

    # final_packager ------------------------------------------------------
    nodes.append(
        AiNodeConfig(
            id="final_packager",
            type="ai",
            name="Final Packager",
            model="gpt-3.5-turbo",
            prompt="Return JSON with keys summary and stats from the provided data.",
            llm_config=llm_cfg,
            dependencies=["summarise_video"],
            input_mappings={
                "summary": InputMapping(source_node_id="summarise_video", source_output_key="output"),
            },
        )
    )

    # ----------------------------------------------------------------------
    # 5. Create context manager & register stubs ---------------------------
    # ----------------------------------------------------------------------
    ctx_mgr = GraphContextManager()
    ctx_mgr.register_tool(StubHttpTool())
    ctx_mgr.register_tool(StubWebSearchTool())

    # ----------------------------------------------------------------------
    # 6. Run chain ---------------------------------------------------------
    # ----------------------------------------------------------------------

    async def _run():
        chain = ScriptChain(
            nodes=nodes,
            name="demo_content_repurposer",
            context_manager=ctx_mgr,
            max_parallel=3,
        )
        result = await chain.execute()
        print("\n=== FINAL OUTPUT ===")
        print(result.output)
        print("\n=== METRICS ===")
        print(result.token_stats)

    asyncio.run(_run())


if __name__ == "__main__":
    main() 