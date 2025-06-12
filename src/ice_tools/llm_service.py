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
    # Provide stub error types when OpenAI package is absent (e.g., during tests).
    class _StubError(Exception):
        ...

    class _OpenAIErrorModule:  # type: ignore
        RateLimitError = _StubError
        Timeout = _StubError
        APIError = _StubError

    openai_error = _OpenAIErrorModule()  # type: ignore[var-annotated]

logger = logging.getLogger(__name__)


class LLMService:
    """High-level helper for synchronous/asynchronous LLM calls.

    Delegates the actual HTTP interaction to provider-specific *handler* classes
    located in ``ice_tools.llm_providers`` and offers:

    • Automatic provider dispatch based on ``LLMConfig.provider``.
    • Built-in retries with exponential backoff (via *tenacity*).
    • An optional global timeout that wraps the entire request.
    • Error-capture semantics: instead of raising, return ``(text, usage, error)``.
    """

    def __init__(self) -> None:
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
        """Return *(text, usage, error)* from the configured LLM provider."""

        handler = self.handlers.get(llm_config.provider)
        if handler is None:
            return "", None, f"No handler for provider: {llm_config.provider}"

        async def _call_handler() -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
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
            ) as err:
                # Re-raise so *tenacity* can retry.
                raise err
            except Exception as err:  # pylint: disable=broad-except
                # Retry on generic 502/503 HTTP gateway errors.
                if getattr(err, "status", None) in {502, 503}:
                    raise err
                logger.error("LLM handler raised unexpected exception", exc_info=True)
                return "", None, str(err)

        @retry(
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        async def _call_with_retry() -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
            return await _call_handler()

        try:
            if timeout_seconds is None:
                return await _call_with_retry()
            return await asyncio.wait_for(_call_with_retry(), timeout=timeout_seconds)
        except (
            openai_error.RateLimitError,
            openai_error.Timeout,
            openai_error.APIError,
        ) as err:
            logger.warning("LLM request failed after retries: %s", err)
            return "", None, str(err)
        except asyncio.TimeoutError:
            logger.warning("LLM request exceeded overall timeout of %s seconds", timeout_seconds)
            return "", None, "Request timed out"
        except Exception as err:  # pylint: disable=broad-except
            logger.error("Unhandled exception in LLMService.generate", exc_info=True)
            return "", None, str(err) 