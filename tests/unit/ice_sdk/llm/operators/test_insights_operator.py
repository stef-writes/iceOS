from typing import Any, Dict, Optional, Tuple

import json
import pytest

from ice_sdk.llm.operators.insights import InsightsOperator
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
        payload = {"insights": ["Insight 1", "Insight 2", "Insight 3"]}
        return json.dumps(payload), None, None


@pytest.mark.asyncio
async def test_insights_operator(monkeypatch):
    op = InsightsOperator()
    monkeypatch.setattr(op, "llm_service", _StubLLMService())

    summary = "Sales increased by 10% quarter over quarter while costs stayed flat."
    out = await op.process({"summary": summary, "max_tokens": 128})

    assert len(out["insights"]) >= 3 