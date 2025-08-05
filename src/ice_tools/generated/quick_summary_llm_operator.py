"""Quick summarizer"""

from __future__ import annotations
from typing import Any, Dict
from pydantic import Field
from ice_core.base_tool import ToolBase
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry

class QuickSummaryLLMOperator(ToolBase):
    name: str = "quick_summary_llm_operator"
    description: str = Field("Quick summarizer")
    model: str = "gpt-4o"

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:  # noqa: D401
        prompt: str = kwargs.get("prompt", "")
        return {"completion": f"Echo: {prompt}"}

_instance = QuickSummaryLLMOperator()
registry.register_instance(NodeType.LLM, _instance.name, _instance)  # type: ignore[arg-type]
