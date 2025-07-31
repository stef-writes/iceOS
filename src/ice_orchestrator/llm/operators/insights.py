from __future__ import annotations

"""InsightsOperator – generates 3-5 actionable insights from a summary."""

import json
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ice_core.models.llm import ModelProvider
from ice_orchestrator.llm.operators.base import LLMOperator, LLMOperatorConfig
from ice_core.llm.service import LLMService

__all__: list[str] = ["InsightsOperator"]

class _Input(BaseModel):
    summary: str = Field(..., min_length=20)
    max_tokens: int = Field(256, ge=64, le=512)

class _Output(BaseModel):
    insights: List[str]

class InsightsOperator(LLMOperator):
    name: str = "insights"
    description: str = "Generate step-by-step actionable insights from a dataset summary."

    InputModel: type[_Input] = _Input
    OutputModel: type[_Output] = _Output

    def __init__(
        self,
        *,
        config: Optional[LLMOperatorConfig] = None,
        llm_service: Optional[LLMService] = None,
    ) -> None:
        if config is None:
            provider = ModelProvider.OPENAI
            model = "gpt-4o"
            if os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
                provider = ModelProvider.ANTHROPIC
                model = "claude-3-sonnet-20240229"
            config = LLMOperatorConfig(provider=provider, model=model, max_tokens=256, temperature=0.3)
        super().__init__(config=config)
        self.llm_service = llm_service or LLMService()

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        inp = self.InputModel(**data)

        prompt = (
            "You are an inventory analyst. Given the following summary of CSV data, "
            "think step-by-step and produce 3-5 actionable insights.\n\n"
            f"CSV Summary:\n{inp.summary}\n\n"
            "Return JSON with the key 'insights' containing the list of insights."
        )

        # sync config token limit
        self.config.max_tokens = inp.max_tokens  # type: ignore[attr-defined]

        text = await self.generate(prompt)

        # Try JSON extraction
        try:
            data_obj = json.loads(text)
            insights_list = data_obj.get("insights")
            if isinstance(insights_list, list):
                return {"insights": insights_list}
        except Exception:
            pass

        # Fallback parsing
        items = [ln.strip("- •\u2022 ") for ln in text.splitlines() if ln.strip()]
        return {"insights": items[:5]}

 