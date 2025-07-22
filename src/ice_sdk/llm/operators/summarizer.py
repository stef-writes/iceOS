from __future__ import annotations

"""SummarizerOperator – summarises tabular row data using an LLM.

Replaces the old `summarizer_skill` implementation.
"""

import json
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ice_core.models.llm import LLMConfig as CoreLLMConfig, ModelProvider
from ice_sdk.llm.operators.base import LLMOperator, LLMOperatorConfig
from ice_sdk.providers.llm_service import LLMService
from ice_core.utils.deprecation import deprecated

__all__: list[str] = ["SummarizerOperator"]


class _Input(BaseModel):
    rows: List[Dict[str, Any]] | str = Field(..., description="Rows as list or JSON")
    max_summary_tokens: int = Field(128, ge=16, le=1024)

    @field_validator("rows", mode="before")
    @classmethod
    def _parse_rows(cls, v):  # noqa: D401
        if isinstance(v, str):
            return json.loads(v)
        return v


class _Output(BaseModel):
    summary: str


class SummarizerOperator(LLMOperator):
    name: str = "summarizer"
    description: str = "Summarize structured tabular data into natural language."

    InputModel = _Input  # type: ignore[assignment]
    OutputModel = _Output  # type: ignore[assignment]

    def __init__(
        self,
        *,
        config: Optional[LLMOperatorConfig] = None,
        llm_service: Optional[LLMService] = None,
    ) -> None:
        # Choose provider/model dynamically (same logic as old skill) --------
        if config is None:
            if os.getenv("OPENAI_API_KEY"):
                provider = ModelProvider.OPENAI
                model = "gpt-4o"
            elif os.getenv("ANTHROPIC_API_KEY"):
                provider = ModelProvider.ANTHROPIC
                model = "claude-3-sonnet-20240229"
            else:
                provider = ModelProvider.OPENAI  # Default; will trigger offline path
                model = "gpt-4o"

            config = LLMOperatorConfig(provider=provider, model=model, max_tokens=256, temperature=0.3)

        self.config = config
        self.llm_service = llm_service or LLMService()

    # ------------------------------------------------------------------
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        inp = self.InputModel(**data)

        # Offline fallback when no API key available ------------------------
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            row_count = len(inp.rows)  # type: ignore[arg-type]
            headers = list(inp.rows[0].keys()) if inp.rows else []  # type: ignore[arg-type]
            return {"summary": f"Dataset has {row_count} rows with columns: {', '.join(headers)}."}

        dataset_preview = json.dumps(inp.rows[:10], indent=2)  # type: ignore[arg-type]
        prompt = (
            "You are a data summarization assistant. Given the following rows\n"
            f"(maximum 10 shown) from a CSV dataset, produce a concise summary\n"
            f"under {inp.max_summary_tokens} tokens describing key observations,\n"
            "value ranges, and any outliers.\n\n"
            f"Rows Preview:\n{dataset_preview}\n\nSummary:"
        )

        # Ensure config max_tokens matches request -------------------------
        self.config.max_tokens = inp.max_summary_tokens  # type: ignore[attr-defined]

        text = await self.generate(prompt)
        return {"summary": text.strip()}


# ---------------------------------------------------------------------------
# Deprecation shim -----------------------------------------------------------
# ---------------------------------------------------------------------------

@deprecated("0.5.0", replacement="ice_sdk.llm.operators.SummarizerOperator")
class SummarizerSkillShim:  # pylint: disable=too-few-public-methods
    def __getattr__(self, item: str) -> Any:  # noqa: D401
        raise AttributeError("SummarizerSkill is deprecated. Use SummarizerOperator instead.") 