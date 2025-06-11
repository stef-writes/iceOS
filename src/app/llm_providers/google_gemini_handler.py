import logging
import os
from typing import Any, Dict, Optional, Tuple

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.models.config import LLMConfig

from .base_handler import BaseLLMHandler

logger = logging.getLogger(__name__)


class GoogleGeminiHandler(BaseLLMHandler):
    """Handler for Google Gemini LLM provider."""

    async def generate_text(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: Dict[str, Any],  # Context might be used for more advanced scenarios
        tools: Optional[list] = None,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        """Generate text using the Google Gemini API. 'tools' is ignored for now."""
        api_key = llm_config.api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "", None, "API key for Google Gemini is missing."

        try:
            # Configuring the API key for each call might be slightly inefficient
            # but ensures thread safety and that the correct key is used if it can change.
            # Alternatively, this could be done once at application startup if the key is static.
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel(llm_config.model)

            # Map LLMConfig parameters to GenerationConfig
            # Gemini uses 'candidate_count', 'stop_sequences', 'max_output_tokens', 'temperature', 'top_p', 'top_k'
            # We need to ensure our llm_config fields are correctly mapped.
            generation_config_params = {
                "temperature": (
                    llm_config.temperature
                    if llm_config.temperature is not None
                    else None
                ),
                "top_p": llm_config.top_p if llm_config.top_p is not None else None,
                "top_k": (
                    llm_config.custom_parameters.get("top_k")
                    if "top_k" in llm_config.custom_parameters
                    else None
                ),
                "max_output_tokens": (
                    llm_config.max_tokens if llm_config.max_tokens is not None else None
                ),
                # "stop_sequences": llm_config.stop_sequences if llm_config.stop_sequences else None # Needs to be a list of strings
            }

            # Add custom parameters if they exist and match GenerationConfig fields
            if llm_config.custom_parameters:
                for key, value in llm_config.custom_parameters.items():
                    if key in [
                        "candidate_count",
                        "stop_sequences",
                    ]:  # Add other valid GenerationConfig keys here
                        generation_config_params[key] = value

            # Filter out None values, as GenerationConfig expects actual values or to omit the param
            filtered_gen_config_params = {
                k: v for k, v in generation_config_params.items() if v is not None
            }

            gen_config = GenerationConfig(**filtered_gen_config_params)

            logger.debug(
                f"Sending request to Google Gemini: model={llm_config.model}, prompt_length={len(prompt)}, config={filtered_gen_config_params}"
            )

            response = await model.generate_content_async(
                prompt, generation_config=gen_config
            )

            logger.debug(f"Received response from Google Gemini: {response}")

            text_content = ""
            if response.parts:
                text_content = "".join(
                    part.text for part in response.parts if hasattr(part, "text")
                ).strip()
            elif response.text:  # Fallback for simpler text responses
                text_content = response.text.strip()

            if (
                not text_content
                and response.prompt_feedback
                and response.prompt_feedback.block_reason
            ):
                block_reason_message = (
                    response.prompt_feedback.block_reason_message or "Content blocked"
                )
                logger.warning(
                    f"Google Gemini generation blocked. Reason: {response.prompt_feedback.block_reason}, Message: {block_reason_message}"
                )
                return (
                    "",
                    None,
                    f"Google Gemini generation failed: {block_reason_message}",
                )

            if not text_content:
                logger.warning(
                    f"Google Gemini response missing expected text content: {response}"
                )
                return "", None, "Google Gemini response missing text content."

            # Token usage: Google Gemini API for generate_content (non-chat)
            # does not directly return token counts in the main response object in the same way as OpenAI/Anthropic.
            # It's often part of `response.usage_metadata` if available, or obtained via a separate token counting method.
            # For now, we'll return None for usage, or try to infer if model allows.
            # The `count_tokens` method can be used: `model.count_tokens(prompt)` for input. Output needs to be counted similarly.
            usage_stats = None
            # Placeholder for token counting - this is often more complex with Gemini for output tokens.
            # prompt_tokens = model.count_tokens(prompt).total_tokens
            # completion_tokens = model.count_tokens(text_content).total_tokens
            # usage_stats = {
            #     "prompt_tokens": prompt_tokens,
            #     "completion_tokens": completion_tokens,
            #     "total_tokens": prompt_tokens + completion_tokens
            # }
            # For now, actual token count from API response is not straightforward for generate_content for all models.
            # If `response.usage_metadata` exists and contains relevant fields, use it.
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage_stats = {
                    "prompt_tokens": (
                        response.usage_metadata.prompt_token_count
                        if hasattr(response.usage_metadata, "prompt_token_count")
                        else 0
                    ),
                    "completion_tokens": (
                        response.usage_metadata.candidates_token_count
                        if hasattr(response.usage_metadata, "candidates_token_count")
                        else 0
                    ),  # Or equivalent field
                    "total_tokens": (
                        response.usage_metadata.total_token_count
                        if hasattr(response.usage_metadata, "total_token_count")
                        else 0
                    ),
                }
                if (
                    usage_stats["prompt_tokens"] == 0
                    and usage_stats["total_tokens"] > 0
                    and usage_stats["completion_tokens"] == 0
                ):  # sometimes only total is populated
                    # This is a guess, better to use specific fields if available
                    pass

            return text_content, usage_stats, None

        except Exception as e:
            logger.error(
                f"Error during Google Gemini API call: {str(e)}", exc_info=True
            )
            # Classify Gemini-specific exceptions if needed
            return "", None, f"Google Gemini API Error: {str(e)}"
