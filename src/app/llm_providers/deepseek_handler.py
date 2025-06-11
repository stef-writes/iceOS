import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

from openai import AsyncOpenAI

from app.models.config import LLMConfig

from .base_handler import BaseLLMHandler

logger = logging.getLogger(__name__)

# It's good practice to define the base URL as a constant or get it from config
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"  # Or os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com/v1")


class DeepSeekHandler(BaseLLMHandler):
    """Handler for DeepSeek LLM provider, using OpenAI SDK compatibility."""

    async def generate_text(
        self,
        llm_config: LLMConfig,
        prompt: str,  # This is the fully resolved user prompt
        context: Dict[str, Any],  # Context for potential system prompts etc.
        tools: Optional[list] = None,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        """Generate text using the DeepSeek API via OpenAI SDK. 'tools' is ignored for now."""
        # Prioritize DEEPSEEK_API_KEY from environment for DeepSeek provider
        api_key = os.getenv("DEEPSEEK_API_KEY")

        # If not in env, try the one from llm_config (e.g. passed in request for this specific provider)
        if not api_key:
            api_key = llm_config.api_key

        if not api_key:
            logger.error(
                "API key for DeepSeek is missing. Ensure DEEPSEEK_API_KEY is set in .env or llm_config.api_key is provided for DeepSeek requests."
            )
            return (
                "",
                None,
                "API key for DeepSeek is missing. Set DEEPSEEK_API_KEY or provide in llm_config specifically for DeepSeek.",
            )

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=llm_config.custom_parameters.get(
                "base_url", DEEPSEEK_BASE_URL
            ),  # Allow override from custom_parameters
        )

        messages = [{"role": "user", "content": prompt}]

        system_prompt_content = context.get("system_prompt")
        if system_prompt_content:
            messages.insert(0, {"role": "system", "content": system_prompt_content})

        try:
            logger.info(
                f"🔄 Making DeepSeek API call: model={llm_config.model}, max_tokens={llm_config.max_tokens}"
            )
            logger.debug(
                f"Sending request to DeepSeek (via OpenAI SDK): model={llm_config.model}, messages_count={len(messages)}, temp={llm_config.temperature}, max_tokens={llm_config.max_tokens}"
            )

            # Ensure custom_parameters are passed correctly if any
            request_params = {
                "model": llm_config.model,
                "messages": messages,
                "max_tokens": llm_config.max_tokens,
                "temperature": llm_config.temperature,
                "top_p": llm_config.top_p,
                # "stream": False, # stream is not typically set here for non-streaming calls
                # "stop": llm_config.stop_sequences, # handle if format matches
            }
            if llm_config.custom_parameters:
                request_params.update(llm_config.custom_parameters)

            response = await client.chat.completions.create(**request_params)

            text_content = ""
            if response.choices and response.choices[0].message:
                msg = response.choices[0].message
                if hasattr(msg, "function_call") and msg.function_call:
                    # If it's a function call, return it as a JSON string
                    try:
                        arguments = json.loads(msg.function_call.arguments)
                    except json.JSONDecodeError:
                        logger.error(
                            f"Malformed function_call arguments: {msg.function_call.arguments}"
                        )
                        return (
                            "",
                            None,
                            f"Malformed function_call arguments: {msg.function_call.arguments}",
                        )
                    text_content = json.dumps(
                        {
                            "function_call": {
                                "name": msg.function_call.name,
                                "arguments": arguments,
                            }
                        }
                    )
                    logger.info(f"📝 Generated content preview:\n{text_content}")
                    return text_content, None, None
                elif msg.content:
                    text_content = msg.content.strip()

            logger.info(
                f"✅ DeepSeek API call completed: {len(text_content) if text_content else 0} chars"
            )

            # Add content preview
            if text_content:
                preview = (
                    text_content[:200] + "..."
                    if len(text_content) > 200
                    else text_content
                )
                logger.info(f"📝 Generated content preview:\n{preview}")

            logger.debug(
                f"Received response from DeepSeek (via OpenAI SDK): {response}"
            )

            if not text_content:
                finish_reason = (
                    response.choices[0].finish_reason if response.choices else None
                )
                if finish_reason == "length":
                    logger.warning(
                        f"DeepSeek generation stopped due to: {finish_reason}. Max tokens: {llm_config.max_tokens}"
                    )
                    return (
                        "",
                        None,
                        f"DeepSeek generation stopped due to {finish_reason} (possibly max_tokens).",
                    )
                logger.warning(
                    f"DeepSeek response missing expected text content: {response}"
                )
                return "", None, "DeepSeek response missing content."

            usage_stats = None
            if response.usage:
                usage_stats = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return text_content, usage_stats, None

        except Exception as e:
            logger.error(
                f"Error during DeepSeek API call (via OpenAI SDK): {str(e)}",
                exc_info=True,
            )
            # Consider more specific error handling for OpenAI SDK exceptions if needed
            return "", None, f"DeepSeek API Error (via OpenAI SDK): {str(e)}"
