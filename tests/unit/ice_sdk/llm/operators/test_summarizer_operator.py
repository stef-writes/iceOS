from typing import Any, Dict

import pytest

from ice_sdk.llm.operators.summarizer import SummarizerOperator
from ice_core.models import LLMConfig


class _StubLLMService:  # pylint: disable=too-few-public-methods
    async def generate(self, prompt: str, config: LLMConfig) -> Dict[str, Any]:
        """Match the actual LLMService interface."""
        _ = (prompt, config)
        return {"content": "This is a concise summary."}


@pytest.mark.asyncio
async def test_summarizer_operator(monkeypatch):
    op = SummarizerOperator()
    monkeypatch.setattr(op, "llm_service", _StubLLMService())

    rows = [{"item": "apple", "qty": 3}, {"item": "banana", "qty": 5}]
    out = await op.process({"rows": rows, "max_summary_tokens": 64})

    assert "summary" in out
    assert isinstance(out["summary"], str) 