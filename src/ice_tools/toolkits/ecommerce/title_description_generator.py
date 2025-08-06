"""TitleDescriptionGeneratorTool – generate listing copy via LLM.

Supports `test_mode` for offline unit tests.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from pydantic import Field, PositiveFloat

from ice_core.base_tool import ToolBase
from ice_core.exceptions import ValidationError
from ice_core.llm.service import LLMService
from ice_core.models import LLMConfig, ModelProvider
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry

__all__: list[str] = ["TitleDescriptionGeneratorTool"]

logger = logging.getLogger(__name__)


class TitleDescriptionGeneratorTool(ToolBase):
    """Generate marketplace-friendly title & description for one item."""

    # Metadata ----------------------------------------------------------------
    name: str = "title_description_generator"
    description: str = "Generate catchy title & description using LLM."

    # Schema -------------------------------------------------------------------
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:  # noqa: D401 – override
        return {
            "type": "object",
            "properties": {
                "item": {"type": "object"},
            },
            "required": ["item"],
            "additionalProperties": False,
        }

    # Config ------------------------------------------------------------------
    model: str = Field("gpt-4o", description="LLM model name")
    temperature: PositiveFloat = Field(0.7, le=2.0, description="Sampling temperature")
    test_mode: bool = False

    _PROMPT_TEMPLATE: str = (
        "You are an expert e-commerce copywriter. Given the JSON below, "
        "generate a concise *title* (max 80 chars) and a persuasive "
        "*description* (max 300 chars). Respond in JSON with keys 'title' "
        "and 'description' only.\n\nProduct JSON:\n{item_json}"
    )

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:  # noqa: D401
        item: dict[str, Any] = kwargs.get("item", {})
        if "name" not in item:
            raise ValidationError("'item' must include at least a 'name' field")

        if self.test_mode:
            title = f"TEST {item['name'][:50]}"
            desc = f"Test listing for {item['name']} (SKU {item.get('sku', '?')})."
            return {"title": title, "description": desc}

        llm_config = LLMConfig(
            provider=ModelProvider.OPENAI,
            model=self.model,
            temperature=self.temperature,
            max_tokens=256,
        )

        prompt = self._PROMPT_TEMPLATE.format(
            item_json=json.dumps(item, ensure_ascii=False)
        )
        service = LLMService()
        generated_text, _usage, error = await service.generate(llm_config, prompt)
        if error:
            raise ValidationError(f"LLM error: {error}")

        try:
            data = json.loads(generated_text)
            return {"title": data["title"], "description": data["description"]}
        except Exception:
            # Fallback to raw text heuristics
            title = generated_text.strip().split("\n")[0][:80]
            desc = generated_text.strip()[:300]
            return {"title": title, "description": desc}


# Factory function for creating TitleDescriptionGeneratorTool instances
def create_title_description_generator_tool(
    model: str = "gpt-4o",
    temperature: float = 0.7,
    test_mode: bool = False
) -> TitleDescriptionGeneratorTool:
    """Create a TitleDescriptionGeneratorTool with the specified configuration."""
    return TitleDescriptionGeneratorTool(
        model=model,
        temperature=temperature,
        test_mode=test_mode
    )

# Auto-registration -----------------------------------------------------------
from ice_core.unified_registry import register_tool_factory

register_tool_factory("title_description_generator", "ice_tools.toolkits.ecommerce.title_description_generator:create_title_description_generator_tool")
