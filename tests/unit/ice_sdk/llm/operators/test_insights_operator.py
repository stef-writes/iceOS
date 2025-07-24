from typing import Any, Dict, Optional, Tuple

import json
import pytest

from ice_sdk.llm.operators.insights import InsightsOperator
from ice_core.models import LLMConfig


class _StubLLMService:  # pylint: disable=too-few-public-methods
    async def generate(self, prompt: str, config: LLMConfig) -> Dict[str, Any]:
        """Match the actual LLMService interface."""
        _ = (prompt, config)
        payload = {"insights": ["Insight 1", "Insight 2", "Insight 3"]}
        return {"content": json.dumps(payload)}


@pytest.mark.asyncio
async def test_insights_operator(monkeypatch):
    op = InsightsOperator()
    monkeypatch.setattr(op, "llm_service", _StubLLMService())

    summary = "Sales increased by 10% quarter over quarter while costs stayed flat."
    out = await op.process({"summary": summary, "max_tokens": 128})

    assert len(out["insights"]) >= 3 