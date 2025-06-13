from __future__ import annotations

from typing import Any, Dict

import pytest

from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.providers.llm_service import LLMService


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", [
    ModelProvider.OPENAI,
    ModelProvider.ANTHROPIC,
    ModelProvider.GOOGLE,
    ModelProvider.DEEPSEEK,
])
async def test_llm_service_dispatch(monkeypatch, provider):
    """Ensure LLMService dispatches to the correct provider handler and passes
    through the prompt/context intact."""

    service = LLMService()

    model_map = {
        ModelProvider.OPENAI: "gpt-3.5-turbo",
        ModelProvider.ANTHROPIC: "claude-2",
        ModelProvider.GOOGLE: "gemini-1.0-pro-latest",
        ModelProvider.DEEPSEEK: "deepseek-llm",
    }

    llm_config = LLMConfig(provider=provider, model=model_map[provider])

    captured: Dict[str, Any] = {}

    async def _fake_generate_text(*, llm_config, prompt, context, tools):  # noqa: D401
        captured["provider"] = provider
        captured["prompt"] = prompt
        captured["context"] = context
        captured["tools"] = tools
        # Return text, usage, error (usage & error can be None)
        return "OK", {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}, None

    # Monkeypatch the underlying handler for the provider -------------------
    handler = service.handlers[provider]
    monkeypatch.setattr(handler, "generate_text", _fake_generate_text, raising=True)

    text, usage, error = await service.generate(
        llm_config=llm_config,
        prompt="Hello",
        context={"foo": "bar"},
        tools=[{"name": "noop"}],
    )

    assert error is None
    assert text == "OK"
    assert captured["provider"] == provider
    assert captured["prompt"] == "Hello"
    assert captured["context"] == {"foo": "bar"}
    assert captured["tools"] == [{"name": "noop"}] 