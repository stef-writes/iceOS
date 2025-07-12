# ruff: noqa: E402
from __future__ import annotations

"""Anthropic LLM provider handler (migrated)."""

import logging
import os
from typing import Any, Optional

from anthropic import AsyncAnthropic

from ice_sdk.models.config import LLMConfig

from .base_handler import BaseLLMHandler

logger = logging.getLogger(__name__)

__all__: list[str] = ["AnthropicHandler"]


class AnthropicHandler(BaseLLMHandler):
    """Handler for Anthropic Claude models."""

    async def generate_text(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: dict[str, Any],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> tuple[str, Optional[dict[str, int]], Optional[str]]:
        api_key = llm_config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return "", None, "ANTHROPIC_API_KEY not set"

        client = AsyncAnthropic(api_key=api_key)

        system_prompt = context.get("system_prompt")
        system_param = (
            [{"type": "text", "text": system_prompt}] if system_prompt else []
        )

        messages = [{"role": "user", "content": prompt}]
        try:
            async with client:
                response = await client.messages.create(  # type: ignore[call-overload,arg-type]
                    model=str(llm_config.model),
                    system=system_param,  # type: ignore[arg-type]
                    messages=messages,  # type: ignore[arg-type]
                    max_tokens=llm_config.max_tokens or 256,
                    temperature=llm_config.temperature or 1.0,
                    top_p=llm_config.top_p or 1.0,
                )
        except Exception as exc:  # pragma: no cover
            logger.error("Anthropic API error", exc_info=True)
            return "", None, str(exc)

        if (
            response.content
            and isinstance(response.content, list)
            and hasattr(response.content[0], "text")
        ):
            text_content = response.content[0].text.strip()
        else:
            return "", None, "Anthropic response missing text"

        usage_stats = None
        if response.usage:
            usage_stats = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens
                + response.usage.output_tokens,
            }
        return text_content, usage_stats, None
