from __future__ import annotations

import os
from typing import Any, ClassVar, Dict, List, Union

from pydantic import BaseModel, Field, field_validator

from ice_core.models.llm import LLMConfig, ModelProvider
from ice_sdk.providers.llm_service import LLMService

from ...utils.errors import SkillExecutionError
from ..base import SkillBase


class SummarizerInput(BaseModel):
    """Input schema for the summarizer.

    ``rows`` can be supplied as a list of dictionaries **or** as a JSON-encoded
    string (which is convenient when passed through template placeholders).
    """

    rows: Union[List[Dict[str, Any]], str] = Field(
        ..., description="Rows as list or JSON"
    )
    max_summary_tokens: int = Field(128, ge=16, le=1024)

    @field_validator("rows")
    @classmethod
    def parse_rows(cls, value):
        if isinstance(value, str):
            import json

            return json.loads(value)
        return value


class SummarizerOutput(BaseModel):
    """Output schema containing a concise *summary* string."""

    summary: str


class SummarizerSkill(SkillBase):
    """Summarize a list of structured rows using an LLM.

    The skill auto-detects the provider via environment variables:
    • ``OPENAI_API_KEY`` → OpenAI/gpt-4o
    • ``ANTHROPIC_API_KEY`` → Claude/opus
    Fallbacks to a deterministic summary when no key is present so that CI
    remains offline-compatible.
    """

    name: str = "summarizer"
    description: str = "Summarize structured tabular data into natural language."

    InputModel: ClassVar[type[BaseModel]] = SummarizerInput  # type: ignore[assignment]
    OutputModel: ClassVar[type[BaseModel]] = SummarizerOutput  # type: ignore[assignment]

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        try:
            inp = self.InputModel(**kwargs)
        except Exception as exc:
            raise SkillExecutionError(f"Invalid SummarizerSkill input: {exc}") from exc

        # ------------------------------------------------------------------
        # 1. Decide provider based on available API key ---------------------
        # ------------------------------------------------------------------
        if os.getenv("OPENAI_API_KEY"):
            provider = ModelProvider.OPENAI
            model = "gpt-4o"
            api_key_env = "OPENAI_API_KEY"
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = ModelProvider.ANTHROPIC
            model = "claude-3-sonnet-20240229"
            api_key_env = "ANTHROPIC_API_KEY"
        else:
            provider = None  # Offline fallback
            api_key_env = None
            model = None  # type: ignore[assignment]

        # ------------------------------------------------------------------
        # 2. Fallback heuristic when no LLM access --------------------------
        # ------------------------------------------------------------------
        if provider is None:
            row_count = len(inp.rows)
            headers = list(inp.rows[0].keys()) if inp.rows else []
            return {
                "summary": f"Dataset has {row_count} rows with columns: {', '.join(headers)}."
            }

        # ------------------------------------------------------------------
        # 3. Build prompt ---------------------------------------------------
        # ------------------------------------------------------------------
        import json

        dataset_preview = json.dumps(inp.rows[:10], indent=2)
        prompt = (
            "You are a data summarization assistant. Given the following rows\n"
            f"(maximum 10 shown) from a CSV dataset, produce a concise summary\n"
            f"under {inp.max_summary_tokens} tokens describing key observations,\n"
            "value ranges, and any outliers.\n\n"
            f"Rows Preview:\n{dataset_preview}\n\nSummary:"
        )

        llm_cfg = LLMConfig(  # type: ignore[call-arg]
            provider=provider.value,  # use raw str for LLMService
            model=model,
            temperature=0.3,
            max_tokens=inp.max_summary_tokens,
            api_key=os.getenv(api_key_env) if api_key_env else None,
        )

        text, _usage, err = await LLMService().generate(llm_cfg, prompt)
        if err:
            raise SkillExecutionError(f"LLM summarization failed: {err}")

        return {"summary": text.strip()}
