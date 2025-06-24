# ruff: noqa: E402
from __future__ import annotations

"""Abstract base class for LLM provider handlers.

Migrated from ``ice_tools.llm_providers.base_handler`` to the new
``ice_sdk.providers.llm_providers`` namespace.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
import json
import logging

from ice_sdk.models.config import LLMConfig

__all__: list[str] = ["BaseLLMHandler"]

# Shared logger so subclasses can inherit it easily --------------------------
_logger = logging.getLogger(__name__)


class BaseLLMHandler(ABC):
    """Abstract base class for concrete provider handlers."""

    # ---------------------------------------------------------------------
    # Common helpers shared by concrete providers --------------------------
    # ---------------------------------------------------------------------

    @staticmethod
    def _usage_from_openai(resp) -> Optional[Dict[str, int]]:  # noqa: D401
        """Extract *prompt/completion/total* tokens from an OpenAI-style
        response object (also used by DeepSeek which follows the same schema).

        Returns ``None`` when the usage block is absent.
        """

        usage = getattr(resp, "usage", None)
        if not usage:
            return None

        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
        }

    @staticmethod
    def _format_function_call(name: str, arguments_json: str) -> str:  # noqa: D401
        """Convert *function_call* into the compact JSON string shared by SDK.

        The *arguments_json* string is parsed with ``json.loads`` first so we
        can guarantee the output is valid JSON (no random whitespace etc.).
        """

        try:
            arguments = json.loads(arguments_json)
        except json.JSONDecodeError:
            # Bubble up – caller will treat as error path.
            raise

        return json.dumps({
            "function_call": {
                "name": name,
                "arguments": arguments,
            }
        })

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