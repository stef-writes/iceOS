import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

from openai import AsyncOpenAI

from app.models.config import LLMConfig

from .base_handler import BaseLLMHandler

logger = logging.getLogger(__name__)


class OpenAIHandler(BaseLLMHandler):
    """Handler for OpenAI LLM provider."""

    async def generate_text(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: Dict[str, Any],
        tools: Optional[list] = None,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        """Generate text using the OpenAI API with optional function/tool calling support."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Raise an exception so the node can catch it and return success: False
            raise RuntimeError("API key for OpenAI is missing.")

        client = AsyncOpenAI(api_key=api_key)
        messages = []

        # Check for system prompt in context or templates (if you plan to support it via context)
        # For now, assuming simple user prompt model from AiNode
        # You might want to pass self.config.templates from AiNode to here if needed
        # or have a more sophisticated message builder.
        # Example: if "system_message" in context: messages.append({"role": "system", "content": context["system_message"]})

        messages.append({"role": "user", "content": prompt})

        try:
            async with client:
                logger.info(
                    f"🔄 Making OpenAI API call: model={llm_config.model}, max_tokens={llm_config.max_tokens}"
                )
                logger.debug(
                    f"Sending request to OpenAI: model={llm_config.model}, messages={messages}, temp={llm_config.temperature}, max_tokens={llm_config.max_tokens}, tools={tools}"
                )
                response = await client.chat.completions.create(
                    model=llm_config.model,
                    messages=messages,
                    temperature=llm_config.temperature,
                    max_tokens=llm_config.max_tokens,
                    top_p=llm_config.top_p,
                    frequency_penalty=llm_config.frequency_penalty,
                    presence_penalty=llm_config.presence_penalty,
                    stop=llm_config.stop_sequences,
                    functions=tools if tools else None,
                )
                logger.info(
                    f"✅ OpenAI API call completed: {len(response.choices[0].message.content) if response.choices and response.choices[0].message and response.choices[0].message.content else 0} chars"
                )

                # Add content preview
                if (
                    response.choices
                    and response.choices[0].message
                    and response.choices[0].message.content
                ):
                    content = response.choices[0].message.content
                    preview = content[:200] + "..." if len(content) > 200 else content
                    logger.info(f"📝 Generated content preview:\n{preview}")

                logger.debug(f"Received response from OpenAI: {response}")

                text_content = ""
                # Handle function call responses
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
                else:
                    logger.warning(
                        f"OpenAI response missing expected content: {response}"
                    )
                    return "", None, "OpenAI response missing content."

                usage_stats = None
                if hasattr(response, "usage") and response.usage:
                    usage_stats = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }

                return text_content, usage_stats, None

        except Exception as e:
            logger.error(f"Error during OpenAI API call: {str(e)}", exc_info=True)
            return "", None, f"OpenAI API Error: {str(e)}"
