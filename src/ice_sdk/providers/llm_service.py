# ruff: noqa: E402
from __future__ import annotations

"""High-level LLM helper migrated from `ice_tools.llm_service`.

Only importable via::

    from ice_sdk.providers import LLMService

The original module under *ice_tools* re-exports this class for
backwards-compatibility.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

from tenacity import retry, stop_after_attempt, wait_exponential

from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.providers.llm_providers.anthropic_handler import AnthropicHandler
from ice_sdk.providers.llm_providers.deepseek_handler import DeepSeekHandler
from ice_sdk.providers.llm_providers.google_gemini_handler import GoogleGeminiHandler
from ice_sdk.providers.llm_providers.openai_handler import OpenAIHandler

try:
    from openai import error as openai_error  # type: ignore
except Exception:  # pragma: no cover
    # Provide stub error types when OpenAI package is absent (e.g., during tests).
    class _StubError(Exception): ...

    class _OpenAIErrorModule:  # type: ignore
        RateLimitError = _StubError
        Timeout = _StubError
        APIError = _StubError

    openai_error = _OpenAIErrorModule()  # type: ignore[var-annotated]

logger = logging.getLogger(__name__)


class LLMService:
    """High-level helper for synchronous/asynchronous LLM calls.

    Delegates the actual HTTP interaction to provider-specific *handler* classes
    located under ``ice_sdk.providers.llm_providers`` and offers:

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

        # Map provider to enum constant when supplied as raw string
        provider_key: ModelProvider
        try:
            provider_key = (
                (
                    llm_config.provider
                    if isinstance(llm_config.provider, ModelProvider)
                    else ModelProvider(llm_config.provider)  # type: ignore[arg-type]
                )
                if llm_config.provider
                else ModelProvider.OPENAI
            )
        except ValueError:
            return "", None, f"Unsupported provider: {llm_config.provider}"

        handler = self.handlers.get(provider_key)
        if handler is None:
            return "", None, f"No handler for provider: {provider_key}"

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
                openai_error.RateLimitError,  # type: ignore[attr-defined]
                openai_error.Timeout,  # type: ignore[attr-defined]
                openai_error.APIError,  # type: ignore[attr-defined]
            ) as err:  # pragma: no cover – runtime error path
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
        async def _call_with_retry() -> (
            Tuple[str, Optional[Dict[str, int]], Optional[str]]
        ):
            return await _call_handler()

        try:
            if timeout_seconds is None:
                return await _call_with_retry()
            return await asyncio.wait_for(_call_with_retry(), timeout=timeout_seconds)
        except (
            openai_error.RateLimitError,  # type: ignore[attr-defined]
            openai_error.Timeout,  # type: ignore[attr-defined]
            openai_error.APIError,  # type: ignore[attr-defined]
        ) as err:  # pragma: no cover – runtime error path
            logger.warning("LLM request failed after retries: %s", err)
            return "", None, str(err)
        except asyncio.TimeoutError:
            logger.warning(
                "LLM request exceeded overall timeout of %s seconds", timeout_seconds
            )
            return "", None, "Request timed out"
        except Exception as err:  # pylint: disable=broad-except
            logger.error("Unhandled exception in LLMService.generate", exc_info=True)
            return "", None, str(err)
