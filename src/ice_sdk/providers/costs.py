"""Utility for looking-up model pricing and computing cost of a completion.

The tables reflect *per-token* prices in USD.  They are intentionally kept
in a single place so that future provider additions or price changes are a
simple data-edit, not a code change elsewhere in the SDK.

Price data taken from public pricing pages (May 2025).  Feel free to update.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Tuple

from ice_sdk.models.config import ModelProvider

# ---------------------------------------------------------------------------
# Per-token pricing tables ---------------------------------------------------
# ---------------------------------------------------------------------------
# Format:  {model_name: (prompt_price, completion_price)}  – prices in USD
# *prompt_price* applies to input / prompt tokens
# *completion_price* applies to output / completion tokens
#
# NOTE:  Use ``Decimal`` for currency math to avoid FP rounding errors.
# ---------------------------------------------------------------------------

_OPENAI_PRICES: Dict[str, Tuple[Decimal, Decimal]] = {
    #  ✅ Numbers copied from https://openai.com/pricing (2025-05-12)
    "gpt-4o": (Decimal("0.000005"), Decimal("0.000015")),
    "gpt-4o-mini": (Decimal("0.000003"), Decimal("0.000009")),
    "gpt-4-turbo": (Decimal("0.000010"), Decimal("0.000030")),
    "gpt-4": (Decimal("0.000030"), Decimal("0.000060")),
    "gpt-3.5-turbo": (Decimal("0.0000005"), Decimal("0.0000015")),
}

# Mapping by provider --------------------------------------------------------
_PRICING_TABLE: Dict[ModelProvider, Dict[str, Tuple[Decimal, Decimal]]] = {
    ModelProvider.OPENAI: _OPENAI_PRICES,
    # Future providers can be added here, e.g. ModelProvider.ANTHROPIC: {...}
}

# ---------------------------------------------------------------------------
# Public helpers -------------------------------------------------------------
# ---------------------------------------------------------------------------


def get_price_per_token(provider: ModelProvider, model: str) -> Tuple[Decimal, Decimal]:
    """Return *(prompt_price, completion_price)* per token for *model*.

    Raises ``KeyError`` if the model is unknown for the provider.
    """

    try:
        table = _PRICING_TABLE[provider]
        return table[model]
    except KeyError:
        # Unknown model – treat as zero-cost (prevents downstream crashes)
        return Decimal("0"), Decimal("0")


def calculate_cost(
    provider: ModelProvider,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal:
    """Return cost in USD (``Decimal``) for the given token counts."""

    p_price, c_price = get_price_per_token(provider, model)
    return (p_price * prompt_tokens) + (c_price * completion_tokens)


class DemoBudgetEnforcer:
    """Lightweight guard that enforces hard resource ceilings for demos.

    This is *not* a substitute for full usage tracking but provides an
    easy-to-reach safety mechanism for demo code that might otherwise rack up
    unexpected provider costs during workshops or tutorials.
    """

    MAX_LLM_CALLS: int = 3
    MAX_TOOL_EXECUTIONS: int = 5

    def __init__(self) -> None:
        self._llm_calls = 0
        self._tool_execs = 0

    # ------------------------------------------------------------------
    # Event hooks -------------------------------------------------------
    # ------------------------------------------------------------------
    def register_llm_call(self) -> None:
        """Increment LLM call counter and raise if over the cap."""

        self._llm_calls += 1
        if self._llm_calls > self.MAX_LLM_CALLS:
            raise RuntimeError(
                "Demo exceeded allowed LLM call budget (max=%d)" % self.MAX_LLM_CALLS,
            )

    def register_tool_execution(self) -> None:
        """Increment tool execution counter and raise if over the cap."""

        self._tool_execs += 1
        if self._tool_execs > self.MAX_TOOL_EXECUTIONS:
            raise RuntimeError(
                "Demo exceeded allowed tool execution budget (max=%d)"
                % self.MAX_TOOL_EXECUTIONS,
            )

    # ------------------------------------------------------------------
    # Introspection helpers --------------------------------------------
    # ------------------------------------------------------------------
    @property
    def llm_calls(self) -> int:  # noqa: D401 – simple getter
        """Return the number of LLM calls recorded so far."""

        return self._llm_calls

    @property
    def tool_execs(self) -> int:  # noqa: D401 – simple getter
        """Return the number of tool executions recorded so far."""

        return self._tool_execs
