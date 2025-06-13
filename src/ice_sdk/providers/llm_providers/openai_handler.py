# ruff: noqa: E402
from __future__ import annotations

"""OpenAI LLM provider handler (migrated)."""

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

from openai import AsyncOpenAI

from ice_sdk.models.config import LLMConfig

from .base_handler import BaseLLMHandler

logger = logging.getLogger(__name__)

__all__: list[str] = ["OpenAIHandler"]


class OpenAIHandler(BaseLLMHandler):
    """Handler for OpenAI Chat Completions API."""

    async def generate_text(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: Dict[str, Any],
        tools: Optional[list] = None,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        """Generate text (and optional tool/function call) via OpenAI API."""

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "", None, "OPENAI_API_KEY not set"

        client = AsyncOpenAI(api_key=api_key)
        messages: list[dict[str, str]] = []

        # Very simple message construction for now; later integrate templates
        if system := context.get("system_message"):
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            async with client:
                logger.info("🔄 OpenAI call: model=%s", llm_config.model)
                response = await client.chat.completions.create(  # type: ignore[arg-type]
                    model=llm_config.model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=llm_config.temperature,
                    max_tokens=llm_config.max_tokens,
                    top_p=llm_config.top_p,
                    frequency_penalty=llm_config.frequency_penalty,
                    presence_penalty=llm_config.presence_penalty,
                    stop=llm_config.stop_sequences,
                    functions=tools or None,  # type: ignore[arg-type]
                )
        except Exception as exc:  # pragma: no cover – network failures etc.
            logger.error("OpenAI API error", exc_info=True)
            return "", None, str(exc)

        # --------------------------------------------------------------
        # Parse response ------------------------------------------------
        # --------------------------------------------------------------
        choice = response.choices[0].message
        content_str: str = ""
        if getattr(choice, "function_call", None):
            try:
                arguments = json.loads(choice.function_call.arguments)  # type: ignore[union-attr]
            except json.JSONDecodeError:
                return "", None, "Malformed function_call arguments"
            content_str = json.dumps({
                "function_call": {
                    "name": choice.function_call.name,  # type: ignore[union-attr]
                    "arguments": arguments,
                }
            })
        else:
            content_str = (choice.content or "").strip()

        usage_stats: Optional[Dict[str, int]] = None
        if response.usage:
            usage_stats = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return content_str, usage_stats, None 