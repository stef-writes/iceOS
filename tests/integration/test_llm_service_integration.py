"""Integration tests for ``ice_sdk.providers.llm_service.LLMService``.

These tests exercise the full ``LLMService.generate`` call-path including:

1. Provider dispatch – switch on ``LLMConfig.provider`` to pick the correct
   handler.
2. Timeout / retry wrapper inside the public ``generate`` API.
3. Response triple of ``(text, usage, error)``.

A minimal in-process provider handler is registered under the OpenAI provider
slot so the test can run fully offline while still verifying the real
orchestration logic.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pytest
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig  # noqa: WPS301 – re-exported in SDK path
from ice_core.models.model_registry import get_default_model_id  # new import

from ice_sdk.providers.llm_providers.base_handler import BaseLLMHandler
from ice_sdk.providers.llm_service import LLMService


class _EchoHandler(BaseLLMHandler):
    """Simple in-process provider that echoes the prompt back.

    The implementation purposefully mirrors the signature expected by
    :pyclass:`~ice_sdk.providers.llm_providers.base_handler.BaseLLMHandler` so
    that it can be used as a drop-in replacement for any remote provider.
    """

    async def generate_text(  # type: ignore[override]
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: Dict[str, Any],  # noqa: D401 – framework contract
        tools: Optional[list[Dict[str, Any]]] = None,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        """Return the prompt prefixed with ``"echo:"`` plus fake usage stats."""

        token_count = len(prompt.split())
        usage = {
            "prompt_tokens": token_count,
            "completion_tokens": 0,
            "total_tokens": token_count,
        }
        return f"echo: {prompt}", usage, None


@pytest.mark.asyncio
async def test_llm_service_generate_round_trip() -> None:
    """End-to-end verification of ``LLMService.generate`` orchestration."""

    # Arrange ----------------------------------------------------------------
    svc = LLMService()
    svc.handlers[ModelProvider.OPENAI] = _EchoHandler()  # override network call

    cfg = LLMConfig(model=get_default_model_id(), provider=ModelProvider.OPENAI)
    prompt = "Hello integration test"

    # Act --------------------------------------------------------------------
    text, usage, error = await svc.generate(cfg, prompt)

    # Assert -----------------------------------------------------------------
    assert error is None
    assert text == f"echo: {prompt}"
    assert usage == {
        "prompt_tokens": len(prompt.split()),
        "completion_tokens": 0,
        "total_tokens": len(prompt.split()),
    }
