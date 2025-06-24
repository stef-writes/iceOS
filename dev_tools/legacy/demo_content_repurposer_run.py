# Copy of scripts/demo_content_repurposer_run.py – kept for reference
from __future__ import annotations

import asyncio
import sys
from uuid import uuid4

from ice_orchestrator import ScriptChain
from ice_sdk.context.manager import GraphContextManager
from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig, InputMapping
from ice_sdk.tools.base import BaseTool, function_tool, ToolContext

# Stub Slack / web search etc – same as original script -----------------------

CALL_LOG = []

@function_tool(name_override="slack_post")
async def slack_dummy(ctx: ToolContext, channel: str, text: str):  # type: ignore[override]
    CALL_LOG.append({"channel": channel, "text": text})
    return {"sent": True}


class StubHttpTool(BaseTool):
    name = "http_request"
    description = "Stubbed HTTP request"
    parameters_schema = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
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
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    async def run(self, **kwargs):  # type: ignore[override]
        return {"results": [{"title": "Top Hashtags", "url": "https://example.com", "snippet": "#ai #python"}]}


def build_nodes(youtube_url: str):
    llm_cfg = LLMConfig(provider=ModelProvider.OPENAI, model="gpt-3.5-turbo", temperature=0.0)
    nodes = [
        AiNodeConfig(
            id="parse_url",
            type="ai",
            name="Parse URL",
            model="gpt-3.5-turbo",
            prompt="Extract video_id, title and channel from the YouTube URL in JSON.",
            llm_config=llm_cfg,
            input_mappings={"youtube_url": youtube_url},  # type: ignore[arg-type]
            output_schema={"video_id": "str", "title": "str", "channel": "str"},
        ),
        ToolNodeConfig(
            id="fetch_transcript",
            type="tool",
            name="Fetch Transcript",
            tool_name="http_request",
            tool_args={"method": "GET", "url": "https://youtubetranscript.com/?video_id={video_id}"},
            dependencies=["parse_url"],
            input_mappings={"video_id": InputMapping(source_node_id="parse_url", source_output_key="video_id")},
        ),
        AiNodeConfig(
            id="summarise_video",
            type="ai",
            name="Summarise Video",
            model="gpt-3.5-turbo",
            prompt="Provide a concise summary of the transcript.",
            llm_config=llm_cfg,
            dependencies=["fetch_transcript"],
            input_mappings={"transcript": InputMapping(source_node_id="fetch_transcript", source_output_key="body")},
        ),
        AiNodeConfig(
            id="final_packager",
            type="ai",
            name="Final Packager",
            model="gpt-3.5-turbo",
            prompt="Return JSON with keys summary and stats from the provided data.",
            llm_config=llm_cfg,
            dependencies=["summarise_video"],
            input_mappings={"summary": InputMapping(source_node_id="summarise_video", source_output_key="output")},
        ),
    ]
    return nodes


def main():
    if len(sys.argv) < 2:
        print("Usage: python demo_content_repurposer_run.py <youtube_url>")
        sys.exit(1)
    youtube_url = sys.argv[1]

    ctx_mgr = GraphContextManager()
    ctx_mgr.register_tool(StubHttpTool())
    ctx_mgr.register_tool(StubWebSearchTool())

    chain = ScriptChain(nodes=build_nodes(youtube_url), context_manager=ctx_mgr, tools=[slack_dummy])

    print("Running demo chain …")
    asyncio.run(chain.execute())


if __name__ == "__main__":
    main() 