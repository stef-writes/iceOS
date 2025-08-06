"""LLMServiceAdapter (OpenAI-only) – relocated to SDK services.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

try:
    import openai  # – optional
except Exception:
    openai = None  # type: ignore

from pydantic import BaseModel, Field

# LLMService imported directly; ServiceLocator removed
from ice_core.llm.service import LLMService
from ice_core.models import LLMConfig, ModelProvider

__all__: list[str] = ["LLMServiceAdapter"]


class CompletionRequest(BaseModel):
    prompt: str
    model: str = Field(default="gpt-4o")
    max_tokens: int = Field(default=2000, ge=1, le=4096)


class LLMServiceAdapter:
    """Simple wrapper around `LLMService` with sync helper."""

    def __init__(self) -> None:
        self._svc: LLMService | None = None

    @property
    def _service(self) -> Any:
        """Lazy load the LLM service from ServiceLocator."""
        if self._svc is None:
            self._svc = LLMService()
        return self._svc

    async def generate_async(
        self, prompt: str, *, model: str = "gpt-4o", max_tokens: int = 2000
    ) -> Dict[str, Any]:
        if openai is None:
            return {"text": "", "usage": None, "error": "openai package not installed"}

        req = CompletionRequest(prompt=prompt, model=model, max_tokens=max_tokens)
        llm_cfg = LLMConfig(
            provider=ModelProvider.OPENAI, model=req.model, max_tokens=req.max_tokens
        )
        text, usage, error = await self._service.generate(
            llm_config=llm_cfg, prompt=req.prompt
        )
        return {"text": text, "usage": usage, "error": error}

    def generate(
        self, prompt: str, *, model: str = "gpt-4o", max_tokens: int = 2000
    ) -> Dict[str, Any]:
        return asyncio.run(
            self.generate_async(prompt, model=model, max_tokens=max_tokens)
        )
