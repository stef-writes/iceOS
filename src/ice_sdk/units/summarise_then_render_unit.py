from __future__ import annotations

"""SummariseThenRenderUnit – LLM summarisation followed by Jinja render."""

from typing import Any, Dict

from ice_sdk.providers.llm_service import LLMService
from ice_sdk.tools.service import ToolService, ToolRequest
from ice_sdk.registry.unit import global_unit_registry


class SummariseThenRenderUnit:
    name = "summarise_then_render"

    async def validate(self):  # noqa: D401 – simple placeholder
        pass

    async def execute(self, inputs: Dict[str, Any]):
        text = inputs.get("text", "")
        llm_service = LLMService()
        summary, _, _ = await llm_service.generate(
            llm_config={"provider": "openai", "model": "gpt-4o"},
            prompt=f"Summarise the following in 100 tokens or fewer:\n\n{text}",
            context={},
            tools=None,
            timeout_seconds=30,
            max_retries=1,
        )

        tool_service = ToolService()
        rendered = await tool_service.execute(
            ToolRequest(
                tool_name="jinja_render",
                inputs={
                    "template": "<p>{{ summary }}</p>",
                    "context": {"summary": summary},
                },
                context={},
            )
        )

        html = rendered.get("data", {}).get("rendered") if isinstance(rendered, dict) else None
        return {"summary": summary, "html": html}


# Register

global_unit_registry.register("summarise_then_render", SummariseThenRenderUnit()) 