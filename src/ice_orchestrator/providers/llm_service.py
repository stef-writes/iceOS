"""High-level LLM service for managing provider interactions."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Tuple

from tenacity import retry, stop_after_attempt, wait_exponential

from ice_core.models import LLMConfig, ModelProvider
from ice_orchestrator.providers.llm_providers import (
    AnthropicHandler,
    DeepSeekHandler,
    GoogleGeminiHandler,
    OpenAIHandler,
)
from ice_orchestrator.providers.llm_providers.base_handler import BaseLLMHandler

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
    located under ``ice_orchestrator.providers.llm_providers`` and offers:

    • Automatic provider dispatch based on ``LLMConfig.provider``.
    • Built-in retries with exponential backoff (via *tenacity*).
    • An optional global timeout that wraps the entire request.
    • Error-capture semantics: instead of raising, return ``(text, usage, error)``.
    """

    def __init__(self) -> None:
        # Instantiate available handlers only. Optional ones may be *None*
        self.handlers: dict[ModelProvider, BaseLLMHandler] = {}

        if OpenAIHandler is not None:  # Core provider – must be present
            self.handlers[ModelProvider.OPENAI] = OpenAIHandler()

        if AnthropicHandler is not None:
            self.handlers[ModelProvider.ANTHROPIC] = AnthropicHandler()  # type: ignore[call-arg]

        if GoogleGeminiHandler is not None:
            self.handlers[ModelProvider.GOOGLE] = GoogleGeminiHandler()  # type: ignore[call-arg]

        if DeepSeekHandler is not None:
            self.handlers[ModelProvider.DEEPSEEK] = DeepSeekHandler()  # type: ignore[call-arg]

    async def generate(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        *,
        timeout_seconds: Optional[int] = 30,
        max_retries: int = 2,
    ) -> Tuple[str, Optional[dict[str, int]], Optional[str]]:
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

        # MyPy: narrow *handler* to ``BaseLLMHandler`` after None-check.
        if not isinstance(handler, BaseLLMHandler):
            # Should never happen because we validate registry above, but keep runtime guard.
            return "", None, "Invalid handler instance"

        handler_nn: BaseLLMHandler = handler

        # ------------------------------------------------------------------
        # Internal helper with logging --------------------------------------
        # ------------------------------------------------------------------

        async def _call_handler() -> (
            Tuple[str, Optional[dict[str, int]], Optional[str]]
        ):
            # Log configuration + prompt at DEBUG level so that users can
            # inspect exactly what is being sent to the provider when they
            # run with ``ICE_LOG_LEVEL=DEBUG``.

            logger.debug(
                "LLM request | provider=%s model=%s temperature=%s max_tokens=%s\nPrompt:%s",
                provider_key,
                llm_config.model,
                llm_config.temperature,
                llm_config.max_tokens,
                prompt,
            )

            try:
                result_inner = await handler_nn.generate_text(
                    llm_config=llm_config,
                    prompt=prompt,
                    context=context or {},
                    tools=tools,
                )
                # Unpack tuple for logging before returning.
                generated_text, usage_stats, error_msg = result_inner

                logger.debug(
                    "LLM response | error=%s usage=%s\nOutput:%s",
                    error_msg,
                    usage_stats,
                    generated_text,
                )

                return generated_text, usage_stats, error_msg
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
            Tuple[str, Optional[dict[str, int]], Optional[str]]
        ):
            return await _call_handler()

        try:
            if timeout_seconds is None:
                result_any = await _call_with_retry()
            else:
                result_any = await asyncio.wait_for(
                    _call_with_retry(), timeout=timeout_seconds
                )

            # Result type preserved by our annotations above but *asyncio.wait_for*
            # strips it in stubs – cast to silence MyPy when needed.
            return result_any
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
