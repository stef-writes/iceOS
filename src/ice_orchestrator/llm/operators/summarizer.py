from __future__ import annotations

"""SummarizerOperator – summarises tabular row data using an LLM.

Replaces the old `summarizer_tool` implementation.
"""

import json
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ice_core.models import ModelProvider
from ice_orchestrator.llm.operators.base import LLMOperator, LLMOperatorConfig
from ice_core.llm.service import LLMService

__all__: list[str] = ["SummarizerOperator"]

class _Input(BaseModel):
    rows: List[Dict[str, Any]] | str = Field(..., description="Rows as list or JSON")
    max_summary_tokens: int = Field(128, ge=16, le=1024)

    @field_validator("rows", mode="before")
    @classmethod
    def _parse_rows(cls, v: Any) -> List[Dict[str, Any]]:  # noqa: D401
        if isinstance(v, str):
            return json.loads(v)  # type: ignore[no-any-return]
        return v  # type: ignore[no-any-return]

class _Output(BaseModel):
    summary: str

class SummarizerOperator(LLMOperator):
    name: str = "summarizer"
    description: str = "Summarize structured tabular data into natural language."

    InputModel: type[_Input] = _Input
    OutputModel: type[_Output] = _Output

    def __init__(
        self,
        *,
        config: Optional[LLMOperatorConfig] = None,
        llm_service: Optional[LLMService] = None,
    ) -> None:
        # Choose provider/model dynamically (same logic as old tool) --------
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

        super().__init__(config=config)
        self.llm_service = llm_service or LLMService()

    # ------------------------------------------------------------------
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        inp = self.InputModel(**data)

        # Offline fallback when no API key available ------------------------
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            row_count = len(inp.rows)  # type: ignore[arg-type]
            headers = list(inp.rows[0].keys()) if inp.rows else []  # type: ignore[union-attr]
            return {"summary": f"Dataset has {row_count} rows with columns: {', '.join(headers)}."}

        dataset_preview = json.dumps(inp.rows[:10], indent=2)
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

 