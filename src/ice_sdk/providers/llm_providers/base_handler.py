# ruff: noqa: E402
from __future__ import annotations

"""Abstract base class for LLM provider handlers.

Migrated from ``ice_tools.llm_providers.base_handler`` to the new
``ice_sdk.providers.llm_providers`` namespace.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from ice_sdk.models.config import LLMConfig

__all__: list[str] = ["BaseLLMHandler"]


class BaseLLMHandler(ABC):
    """Abstract base class for concrete provider handlers."""

    @abstractmethod
    async def generate_text(
        self,
        llm_config: LLMConfig,
        prompt: str,
        context: Dict[str, Any],
        tools: Optional[list] = None,
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        """Return *(text, usage, error)* from the provider.

        implementer must return:
        • generated_text – str (may be "" on failure)
        • usage – dict with prompt/completion/total tokens or None
        • error – error string or None on success
        """
        raise NotImplementedError 