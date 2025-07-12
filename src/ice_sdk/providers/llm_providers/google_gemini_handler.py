# ruff: noqa: E402
from __future__ import annotations

"""Google Gemini (generative AI) handler (migrated)."""

import logging
import os
from typing import Any, Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from ice_sdk.models.config import LLMConfig

from .base_handler import BaseLLMHandler

logger = logging.getLogger(__name__)

__all__: list[str] = ["GoogleGeminiHandler"]


class GoogleGeminiHandler(BaseLLMHandler):
    """Handler for Google Gemini models via google-generativeai SDK."""

    async def generate_text(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: dict[str, Any],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> tuple[str, Optional[dict[str, int]], Optional[str]]:
        api_key = llm_config.api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "", None, "GOOGLE_API_KEY not set"

        genai.configure(api_key=api_key)
        model_name: str = llm_config.model or "gemini-pro"
        model = genai.GenerativeModel(model_name)

        gen_cfg_params: dict[str, Any] = {
            "temperature": llm_config.temperature,
            "top_p": llm_config.top_p,
            "top_k": llm_config.custom_parameters.get("top_k"),
            "max_output_tokens": llm_config.max_tokens,
            "stop_sequences": llm_config.stop_sequences or None,
        }
        gen_cfg_params = {k: v for k, v in gen_cfg_params.items() if v is not None}
        gen_config = GenerationConfig(**gen_cfg_params)

        try:
            response = await model.generate_content_async(
                prompt, generation_config=gen_config
            )
        except Exception as exc:  # pragma: no cover
            logger.error("Gemini API error", exc_info=True)
            return "", None, str(exc)

        text_content = ""
        if getattr(response, "parts", None):
            text_content = "".join(
                p.text for p in response.parts if hasattr(p, "text")
            ).strip()
        elif getattr(response, "text", None):
            text_content = response.text.strip()

        if not text_content:
            return "", None, "Gemini response missing text"

        usage_stats = None
        _usage = getattr(response, "usage_metadata", None)
        if _usage is not None:
            usage_stats = {
                "prompt_tokens": getattr(_usage, "prompt_token_count", 0),
                "completion_tokens": getattr(_usage, "candidates_token_count", 0),
                "total_tokens": getattr(_usage, "total_token_count", 0),
            }
        return text_content, usage_stats, None
