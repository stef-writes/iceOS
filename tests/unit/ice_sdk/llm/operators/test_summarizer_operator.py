from typing import Any, Dict, Optional, Tuple

import pytest

from ice_sdk.llm.operators.summarizer import SummarizerOperator
from ice_core.models import LLMConfig


class _StubLLMService:  # pylint: disable=too-few-public-methods
    async def generate(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        tools: Optional[list[Dict[str, Any]]] = None,
        *,
        timeout_seconds: Optional[int] = 30,
        max_retries: int = 2,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:  # type: ignore[override]
        _ = (llm_config, prompt, context, tools, timeout_seconds, max_retries)
        return "This is a concise summary.", None, None


@pytest.mark.asyncio
async def test_summarizer_operator(monkeypatch):
    op = SummarizerOperator()
    monkeypatch.setattr(op, "llm_service", _StubLLMService())

    rows = [{"item": "apple", "qty": 3}, {"item": "banana", "qty": 5}]
    out = await op.process({"rows": rows, "max_summary_tokens": 64})

    assert "summary" in out
    assert isinstance(out["summary"], str) 