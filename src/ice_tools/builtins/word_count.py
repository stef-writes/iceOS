from __future__ import annotations

from pydantic import BaseModel, Field

from ice_sdk.models.node_models import WordCountOutput
from ice_sdk.base_tool import BaseTool


class _WordCountParams(BaseModel):
    text: str = Field(..., description="Text to count words of")


class WordCountTool(BaseTool):
    """Return the number of words in the provided text."""

    name: str = "word_count"
    description: str = (
        "Count the words in a given text and return both the count and the original text."
    )
    parameters_schema = _WordCountParams
    output_schema = WordCountOutput

    async def run(self, *, text: str):  # type: ignore[override]
        words = text.strip().split()
        return {
            "word_count": len(words),
            "text": text,
        }
