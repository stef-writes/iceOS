# ruff: noqa: E402
from __future__ import annotations

"""DeepSeek handler (migrated) using OpenAI-compatible endpoint."""

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

from openai import AsyncOpenAI

from ice_sdk.models.config import LLMConfig

from .base_handler import BaseLLMHandler

logger = logging.getLogger(__name__)

__all__: list[str] = ["DeepSeekHandler"]

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class DeepSeekHandler(BaseLLMHandler):
    async def generate_text(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: Dict[str, Any],
        tools: Optional[list] = None,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        api_key = os.getenv("DEEPSEEK_API_KEY") or llm_config.api_key
        if not api_key:
            return "", None, "DEEPSEEK_API_KEY not set"

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=llm_config.custom_parameters.get("base_url", DEEPSEEK_BASE_URL),
        )

        messages = [{"role": "user", "content": prompt}]
        if system_prompt := context.get("system_prompt"):
            messages.insert(0, {"role": "system", "content": system_prompt})

        try:
            response = await client.chat.completions.create(  # type: ignore[arg-type]
                model=llm_config.model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=llm_config.max_tokens,
                temperature=llm_config.temperature,
                top_p=llm_config.top_p,
                **llm_config.custom_parameters,
            )
        except Exception as exc:
            logger.error("DeepSeek API error", exc_info=True)
            return "", None, str(exc)

        choice = response.choices[0].message

        if getattr(choice, "function_call", None):
            try:
                fc_str = self._format_function_call(  # type: ignore[attr-defined]
                    choice.function_call.name,  # type: ignore[union-attr]
                    choice.function_call.arguments,  # type: ignore[union-attr]
                )
            except json.JSONDecodeError:
                return "", None, "Malformed function_call arguments"
            # DeepSeek returns tool call directly; usage not relevant here
            return fc_str, None, None

        text_content = (choice.content or "").strip()
        if not text_content:
            return "", None, "DeepSeek response missing text"

        usage_stats = self._usage_from_openai(response)  # type: ignore[arg-type]

        return text_content, usage_stats, None 