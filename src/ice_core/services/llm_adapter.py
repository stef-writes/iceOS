"""Minimal LLMServiceAdapter (OpenAI-only) wired into ServiceLocator.

The adapter exists so that low-code callers (CLI / HTTP) can request a text
completion without importing *ice_sdk.providers.LLMService* directly.

Design goals (MVP):
1. **Tiny Surface** – `generate(prompt, model="gpt-4o", max_tokens=2000)`.
2. **OpenAI-only** – other providers added later.
3. **Graceful Degradation** – if the OpenAI SDK is absent the call returns an
   explanatory error so demos/tests run without network.
4. **ServiceLocator Auto-registration** – on import the adapter is registered
   under key ``"llm_service"``.
"""

from __future__ import annotations

from typing import Any, Dict

try:
    import openai  # noqa: F401 – optional import for runtime
except Exception:  # pragma: no cover – fallback when package missing
    openai = None  # type: ignore

from pydantic import BaseModel, Field

from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.providers.llm_service import LLMService
from ice_sdk.services import ServiceLocator

__all__: list[str] = ["LLMServiceAdapter"]


class CompletionRequest(BaseModel):
    prompt: str
    model: str = Field(default="gpt-4o")
    max_tokens: int = Field(default=2000, ge=1, le=4096)


class LLMServiceAdapter:
    """Thin wrapper around :class:`ice_sdk.providers.llm_service.LLMService`."""

    def __init__(self) -> None:
        self._svc = LLMService()

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------
    async def generate_async(
        self, prompt: str, *, model: str = "gpt-4o", max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Return ``{"text": str, "usage": dict, "error": str|None}``."""

        if openai is None:
            # SDK not installed – return predictable error
            return {"text": "", "usage": None, "error": "openai package not installed"}

        req = CompletionRequest(prompt=prompt, model=model, max_tokens=max_tokens)
        llm_cfg = LLMConfig(
            provider=ModelProvider.OPENAI, model=req.model, max_tokens=req.max_tokens
        )

        text, usage, error = await self._svc.generate(
            llm_config=llm_cfg, prompt=req.prompt
        )
        return {"text": text, "usage": usage, "error": error}

    def generate(
        self, prompt: str, *, model: str = "gpt-4o", max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Sync wrapper around :meth:`generate_async`."""

        import asyncio

        return asyncio.run(
            self.generate_async(prompt, model=model, max_tokens=max_tokens)
        )


# ----------------------------------------------------------------------
# Auto-register on import for convenience (composition-root may override)
# ----------------------------------------------------------------------
ServiceLocator.register("llm_service", LLMServiceAdapter())
