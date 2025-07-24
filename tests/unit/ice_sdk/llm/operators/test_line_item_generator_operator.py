import asyncio
from typing import Any, Dict, Optional, Tuple

import pytest

from ice_sdk.llm.operators.line_item_generator import LineItemGeneratorOperator
from ice_core.models import LLMConfig


class _DummyLLMService:  # pylint: disable=too-few-public-methods
    """Stub LLMService that returns a canned JSON payload."""

    async def generate(
        self,
        llm_config: LLMConfig,  # noqa: D401 – signature mirrors real service
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        tools: Optional[list[Dict[str, Any]]] = None,
        *,
        timeout_seconds: Optional[int] = 30,
        max_retries: int = 2,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:  # type: ignore[override]
        _ = (llm_config, prompt, context, tools, timeout_seconds, max_retries)
        payload = {
            "row": {"item": "bananas", "qty": "5"},
            "action": "append",
        }
        import json

        return json.dumps(payload), None, None


@pytest.mark.asyncio
async def test_line_item_generator_operator(monkeypatch):  # noqa: D401
    op = LineItemGeneratorOperator()
    # Inject stub service ---------------------------------------------------
    monkeypatch.setattr(op, "llm_service", _DummyLLMService())

    data = {"request_text": "Add 5 bananas", "headers": ["item", "qty"]}

    output = await op.process(data)

    assert output["action"] == "append"
    assert output["row"]["item"] == "bananas"
    assert output["row"]["qty"] == "5" 