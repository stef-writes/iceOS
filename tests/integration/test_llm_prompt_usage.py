"""Integration tests covering prompt assembly & usage accounting for ``LLMService``.

These tests move beyond simple monkey-patching by invoking the *real* service
with an in-process handler so we still run offline.
"""

from __future__ import annotations

import pytest
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig
from ice_core.models.model_registry import get_default_model_id

from ice_sdk.providers.llm_providers.base_handler import BaseLLMHandler
from ice_sdk.providers.llm_service import LLMService


class _EchoUsageHandler(BaseLLMHandler):
    """Echo back prompt and fabricate deterministic usage tokens."""

    async def generate_text(  # type: ignore[override]
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: dict[str, str],  # noqa: D401 – contractual
        tools=None,
    ):
        tokens = len(prompt.split())
        usage = {
            "prompt_tokens": tokens,
            "completion_tokens": 0,
            "total_tokens": tokens,
        }
        return f"echo::{prompt}", usage, None


@pytest.fixture(name="svc")
async def fixture_llm_service() -> LLMService:  # noqa: D401
    svc = LLMService()
    svc.handlers[ModelProvider.OPENAI] = _EchoUsageHandler()
    return svc


@pytest.mark.asyncio
async def test_prompt_usage_accounting(svc: LLMService):
    prompt = "Hello agile AI"
    cfg = LLMConfig(model=get_default_model_id(), provider=ModelProvider.OPENAI)

    text, usage, error = await svc.generate(cfg, prompt)

    assert error is None
    assert text == f"echo::{prompt}"
    assert usage == {
        "prompt_tokens": len(prompt.split()),
        "completion_tokens": 0,
        "total_tokens": len(prompt.split()),
    }


@pytest.mark.asyncio
async def test_timeout_path(svc: LLMService):
    prompt = "Timeout test"
    cfg = LLMConfig(model=get_default_model_id(), provider=ModelProvider.OPENAI)

    text, usage, error = await svc.generate(cfg, prompt, timeout_seconds=0.001)

    # Our Echo handler is instantaneous, so the timeout should *not* fire.
    # This asserts the positive path first.
    assert error is None
    assert text.startswith("echo::")

    # Now force a tiny timeout on a coroutine that sleeps.
    import asyncio

    class _SlowEcho(_EchoUsageHandler):
        async def generate_text(self, llm_config, prompt, context, tools):  # type: ignore[override]
            await asyncio.sleep(0.01)
            return await super().generate_text(llm_config, prompt, context, tools)

    svc.handlers[ModelProvider.OPENAI] = _SlowEcho()

    text2, usage2, error2 = await svc.generate(cfg, prompt, timeout_seconds=0.001)

    assert text2 == ""
    assert usage2 is None
    assert error2 == "Request timed out"
