import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

from tenacity import retry, stop_after_attempt, wait_exponential

from ice_tools.llm_providers.anthropic_handler import AnthropicHandler
from ice_tools.llm_providers.deepseek_handler import DeepSeekHandler
from ice_tools.llm_providers.google_gemini_handler import GoogleGeminiHandler
from ice_tools.llm_providers.openai_handler import OpenAIHandler
from ice_sdk.models.config import LLMConfig, ModelProvider

try:
    from openai import error as openai_error
except Exception:  # pragma: no cover
    # Fallback dummy error types so the retry logic still works even when OpenAI isn't installed.
    class _StubError(Exception):
        pass

    class _OpenAIErrorModule:  # type: ignore
        RateLimitError = _StubError
        Timeout = _StubError
        APIError = _StubError

    openai_error = _OpenAIErrorModule()

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service abstraction for LLM calls. Routes to the correct handler based on provider.
    """

    def __init__(self):
        self.handlers = {
            ModelProvider.OPENAI: OpenAIHandler(),
            ModelProvider.ANTHROPIC: AnthropicHandler(),
            ModelProvider.GOOGLE: GoogleGeminiHandler(),
            ModelProvider.DEEPSEEK: DeepSeekHandler(),
        }

    async def generate(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        tools: Optional[list] = None,
        *,
        timeout_seconds: Optional[int] = 30,
        max_retries: int = 2,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        """
        Generate text using the specified LLM provider.

        Provides built-in retry with exponential back-off and a hard time-out for the
        entire request.  All failures are captured and returned as the *error*
        element of the tuple instead of leaking exceptions upstream.
        """
        provider = llm_config.provider
        handler = self.handlers.get(provider)
        if not handler:
            return "", None, f"No handler for provider: {provider}"

        # Internal helper so we can wrap retry/timeout logic around a single call.
        async def _call_handler() -> (
            Tuple[str, Optional[Dict[str, int]], Optional[str]]
        ):
            try:
                return await handler.generate_text(
                    llm_config=llm_config,
                    prompt=prompt,
                    context=context or {},
                    tools=tools,
                )
            except (
                openai_error.RateLimitError,
                openai_error.Timeout,
                openai_error.APIError,
            ) as e:
                # Re-raise so tenacity can handle retries.
                raise e
            except Exception as e:
                # For non-OpenAI providers we still want to retry on generic 502/503 errors.
                if hasattr(e, "status") and e.status in {502, 503}:
                    raise e
                # Anything else we consider unrecoverable for this service call.
                logger.error("LLM handler raised unexpected exception", exc_info=True)
                return "", None, str(e)

        # Wrap the handler call with retry / back-off.
        @retry(
            stop=stop_after_attempt(max_retries + 1),  # initial attempt + retries
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        async def _call_with_retry() -> (
            Tuple[str, Optional[Dict[str, int]], Optional[str]]
        ):
            return await _call_handler()

        try:
            # Enforce global time-out if requested; otherwise run directly.
            if timeout_seconds is None:
                return await _call_with_retry()
            else:
                return await asyncio.wait_for(
                    _call_with_retry(), timeout=timeout_seconds
                )
        except (openai_error.RateLimitError, openai_error.Timeout) as e:
            logger.warning(
                "LLM request failed after retries due to rate limit / timeout: %s", e
            )
            return "", None, str(e)
        except openai_error.APIError as e:
            logger.warning("LLM request failed after retries due to API error: %s", e)
            return "", None, str(e)
        except asyncio.TimeoutError:
            logger.warning(
                "LLM request exceeded overall timeout of %s seconds", timeout_seconds
            )
            return "", None, "Request timed out"
        except Exception as e:
            logger.error("Unhandled exception in LLMService.generate", exc_info=True)
            return "", None, str(e)
