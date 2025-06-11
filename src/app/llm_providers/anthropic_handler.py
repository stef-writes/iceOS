import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

from anthropic import AsyncAnthropic  # Ensure this matches your installed package

from app.models.config import LLMConfig, ModelProvider

from .base_handler import BaseLLMHandler

logger = logging.getLogger(__name__)


class AnthropicHandler(BaseLLMHandler):
    """Handler for Anthropic LLM provider."""

    async def generate_text(
        self,
        llm_config: LLMConfig,
        prompt: str,  # This is the fully resolved prompt from AiNode
        context: Dict[str, Any],  # Context for potential system prompts or other uses
        tools: Optional[list] = None,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        """Generate text using the Anthropic API. 'tools' is ignored for now."""
        api_key = llm_config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return "", None, "API key for Anthropic is missing."

        client = AsyncAnthropic(api_key=api_key)

        # Anthropic's `messages.create` is preferred. It takes a list of messages.
        # The `prompt` we receive here is the fully formatted user message.
        # We can also look for a system message in the context if our design supports it.
        # For example, if context contained a specific key like "system_prompt_for_anthropic"
        system_prompt_content = context.get("system_prompt")  # Or a more specific key
        # Ensure empty string becomes None, as some APIs prefer None over empty for optional fields.
        if isinstance(system_prompt_content, str) and not system_prompt_content.strip():
            system_prompt_content = None

        messages = []
        # Note: Anthropic recommends that if a system prompt is used,
        # it should be passed to the `system` parameter of `messages.create` directly,
        # and not as a message in the `messages` list for optimal performance.
        # However, to keep the handler interface simple for now, we can include it in messages if context provides it.
        # A more advanced implementation might adjust this.

        # For now, we assume `prompt` is the primary user content.
        # Anthropic expects messages in a specific order, typically starting with user.
        messages.append({"role": "user", "content": prompt})

        # Prepare system prompt for Anthropic, ensuring it's always a list
        if isinstance(system_prompt_content, str) and system_prompt_content.strip():
            system_param = [{"type": "text", "text": system_prompt_content}]
        else:
            system_param = []

        DEFAULT_MAX_TOKENS = 256
        DEFAULT_TEMPERATURE = 1.0
        DEFAULT_TOP_P = 1.0
        max_tokens = (
            llm_config.max_tokens
            if llm_config.max_tokens is not None
            else DEFAULT_MAX_TOKENS
        )
        temperature = (
            llm_config.temperature
            if llm_config.temperature is not None
            else DEFAULT_TEMPERATURE
        )
        top_p = llm_config.top_p if llm_config.top_p is not None else DEFAULT_TOP_P
        if llm_config.max_tokens is None:
            logger.info(
                f"AnthropicHandler: max_tokens not set, using default {DEFAULT_MAX_TOKENS}"
            )
        if llm_config.temperature is None:
            logger.info(
                f"AnthropicHandler: temperature not set, using default {DEFAULT_TEMPERATURE}"
            )
        if llm_config.top_p is None:
            logger.info(
                f"AnthropicHandler: top_p not set, using default {DEFAULT_TOP_P}"
            )

        try:
            async with client:  # AsyncAnthropic client can be used as a context manager
                logger.info(
                    f"🔄 Making Anthropic API call: model={llm_config.model}, max_tokens={max_tokens}"
                )
                logger.debug(
                    f"Sending request to Anthropic: model={llm_config.model}, system_prompt_present={bool(system_param)}, messages_count={len(messages)}, temp={temperature}, max_tokens={max_tokens}"
                )
                logger.info("ANTHROPIC_HANDLER: Preparing to call messages.create.")
                logger.info(f"ANTHROPIC_HANDLER: llm_config.model = {llm_config.model}")
                logger.info(f"ANTHROPIC_HANDLER: system_param = {system_param}")
                logger.info(
                    f"ANTHROPIC_HANDLER: type(system_param) = {type(system_param)}"
                )
                logger.info(f"ANTHROPIC_HANDLER: messages = {messages}")
                logger.info(f"ANTHROPIC_HANDLER: llm_config.max_tokens = {max_tokens}")
                logger.info(
                    f"ANTHROPIC_HANDLER: llm_config.temperature = {temperature}"
                )
                logger.info(f"ANTHROPIC_HANDLER: llm_config.top_p = {top_p}")

                # Prepare kwargs for the API call, only include top_p if it's a valid float
                api_kwargs = {
                    "model": llm_config.model,
                    "system": system_param,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                if isinstance(top_p, float):
                    api_kwargs["top_p"] = top_p
                # Add any custom parameters if not Anthropic
                if llm_config.provider != ModelProvider.ANTHROPIC:
                    api_kwargs.update(llm_config.custom_parameters)

                response = await client.messages.create(**api_kwargs)
                logger.debug(f"Received response from Anthropic: {response}")

                text_content = ""
                if (
                    response.content
                    and isinstance(response.content, list)
                    and len(response.content) > 0
                ):
                    # Check for function calls first
                    if (
                        hasattr(response.content[0], "function_call")
                        and response.content[0].function_call
                    ):
                        # If it's a function call, return it as a JSON string
                        try:
                            arguments = json.loads(
                                response.content[0].function_call.arguments
                            )
                        except json.JSONDecodeError:
                            logger.error(
                                f"Malformed function_call arguments: {response.content[0].function_call.arguments}"
                            )
                            return (
                                "",
                                None,
                                f"Malformed function_call arguments: {response.content[0].function_call.arguments}",
                            )
                        text_content = json.dumps(
                            {
                                "function_call": {
                                    "name": response.content[0].function_call.name,
                                    "arguments": arguments,
                                }
                            }
                        )
                        logger.info(f"📝 Generated content preview:\n{text_content}")
                        return text_content, None, None
                    # Then check for regular text content
                    elif hasattr(response.content[0], "text"):
                        text_content = response.content[0].text.strip()

                logger.info(
                    f"✅ Anthropic API call completed: {len(text_content) if text_content else 0} chars"
                )

                # Add content preview
                if text_content:
                    preview = (
                        text_content[:200] + "..."
                        if len(text_content) > 200
                        else text_content
                    )
                    logger.info(f"📝 Generated content preview:\n{preview}")

                if not text_content:
                    logger.warning(
                        f"Anthropic response missing expected text content: {response}"
                    )
                    # Check stop_reason, e.g., if max_tokens was hit
                    if response.stop_reason == "max_tokens":
                        return (
                            "",
                            None,
                            "Anthropic generation stopped due to max_tokens limit.",
                        )
                    return (
                        "",
                        None,
                        "Anthropic response missing content or content is not text.",
                    )

                usage_stats = None
                if response.usage:
                    usage_stats = {
                        "prompt_tokens": response.usage.input_tokens,
                        "completion_tokens": response.usage.output_tokens,
                        # Anthropic usage object doesn't always have a direct 'total_tokens'.
                        # If needed, it would be input_tokens + output_tokens.
                        "total_tokens": response.usage.input_tokens
                        + response.usage.output_tokens,
                    }

                return text_content, usage_stats, None

        except Exception as e:
            logger.error(f"Error during Anthropic API call: {str(e)}", exc_info=True)
            # You might want to classify Anthropic-specific exceptions here
            return "", None, f"Anthropic API Error: {str(e)}"
