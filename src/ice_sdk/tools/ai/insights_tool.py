from __future__ import annotations

"""InsightsTool – extract actionable insights from a summary using an LLM."""

from typing import Any, ClassVar, Dict, List

from pydantic import BaseModel, Field

from ice_core.models.llm import LLMConfig, ModelProvider

from ...providers.llm_service import LLMService
from ...utils.errors import ToolExecutionError
from ice_sdk.tools.ai.base import AITool

__all__: list[str] = ["InsightsTool"]

class InsightsInput(BaseModel):
    summary: str = Field(..., min_length=20)
    max_tokens: int = Field(256, ge=64, le=512)

class InsightsOutput(BaseModel):
    insights: List[str]

class InsightsTool(AITool):
    name: str = "insights"
    description: str = (
        "Generate step-by-step actionable insights from a dataset summary."
    )

    InputModel: ClassVar[type[BaseModel]] = InsightsInput
    OutputModel: ClassVar[type[BaseModel]] = InsightsOutput

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        try:
            inp = self.InputModel(**kwargs)
        except Exception as exc:
            raise ToolExecutionError("insights", f"Invalid InsightsTool input: {exc}") from exc

        prompt = (
            "You are an inventory analyst. Given the following summary of CSV data, "
            "think step-by-step and produce 3-5 actionable insights.\n\n"
            f"CSV Summary:\n{inp.summary}\n\n"
            "Return JSON with the key 'insights' containing the list of insights."
        )

        llm_cfg = LLMConfig(  # type: ignore[call-arg]
            provider=ModelProvider.OPENAI.value,
            model="gpt-4o",
            max_tokens=inp.max_tokens,
            temperature=0.3,
        )

        text, _usage, err = await LLMService().generate(llm_cfg, prompt)
        if err:
            raise ToolExecutionError(err)

        # Best-effort JSON extraction ---------------------------------
        import json

        try:
            data = json.loads(text)
            insights = data.get("insights")
            if isinstance(insights, list):
                return {"insights": insights}
        except Exception:
            pass

        # Fallback – split by bullet or newline -----------------------
        items = [ln.strip("- •\u2022 ") for ln in text.splitlines() if ln.strip()]
        return {"insights": items[:5]}
