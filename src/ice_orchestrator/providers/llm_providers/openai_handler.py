# ruff: noqa: E402
from __future__ import annotations

"""OpenAI LLM provider handler (migrated)."""

import json
import logging
import os
from typing import Any, Optional

from openai import AsyncOpenAI

from ice_core.models.model_registry import get_default_model_id
from ice_core.models import LLMConfig

from .base_handler import BaseLLMHandler

logger = logging.getLogger(__name__)

__all__: list[str] = ["OpenAIHandler"]

class OpenAIHandler(BaseLLMHandler):
    """Handler for OpenAI Chat Completions API."""

    async def generate_text(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: dict[str, Any],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> tuple[str, Optional[dict[str, int]], Optional[str]]:
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
                model_name: str = llm_config.model or get_default_model_id()
                response = await client.chat.completions.create(  # type: ignore[arg-type,misc]
                    model=model_name,
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

        # Handle optional function call -----------------------------------
        if getattr(choice, "function_call", None):
            try:
                content_str = self._format_function_call(  # type: ignore[attr-defined]
                    choice.function_call.name,  # type: ignore[union-attr]
                    choice.function_call.arguments,  # type: ignore[union-attr]
                )
            except json.JSONDecodeError:
                return "", None, "Malformed function_call arguments"
        else:
            content_str = (choice.content or "").strip()

        usage_stats = self._usage_from_openai(response)  # type: ignore[arg-type]

        return content_str, usage_stats, None
