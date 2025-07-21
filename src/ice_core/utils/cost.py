"""Utility helpers for *predicting* chain execution cost.

This module is **self-contained** (no imports from higher layers) so that
`ice_core` remains free of upward dependencies.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Tuple

from ice_core.models.enums import ModelProvider

__all__: list[str] = ["estimate_chain_cost"]

# ---------------------------------------------------------------------------
# Minimal per-token pricing table (USD)
# ---------------------------------------------------------------------------
# Only OpenAI prices included for now; extend as needed.
_OPENAI_PRICES: Dict[str, Tuple[Decimal, Decimal]] = {
    "gpt-4o": (Decimal("0.000005"), Decimal("0.000015")),
    "gpt-4o-mini": (Decimal("0.000003"), Decimal("0.000009")),
    "gpt-4-turbo": (Decimal("0.000010"), Decimal("0.000030")),
    "gpt-4": (Decimal("0.000030"), Decimal("0.000060")),
    "gpt-3.5-turbo": (Decimal("0.0000005"), Decimal("0.0000015")),
    "gpt-4-turbo-2024-04-09": (Decimal("0.000010"), Decimal("0.000030")),
}

_PRICING_TABLE: Dict[ModelProvider, Dict[str, Tuple[Decimal, Decimal]]] = {
    ModelProvider.OPENAI: _OPENAI_PRICES,
}


def _get_price_per_token(
    provider: ModelProvider, model: str
) -> Tuple[Decimal, Decimal]:
    """Return *(prompt_price, completion_price)* for *model* or zeros if unknown."""

    return _PRICING_TABLE.get(provider, {}).get(model, (Decimal("0"), Decimal("0")))


# ---------------------------------------------------------------------------
# Public helper -------------------------------------------------------------
# ---------------------------------------------------------------------------


def estimate_chain_cost(chain_spec: Dict[str, Any]) -> float:
    """Return rough USD cost for *chain_spec* without external dependencies."""

    total: Decimal = Decimal("0")

    for node in chain_spec.get("nodes", []):
        if node.get("type") not in {"ai", "llm"}:
            continue

        provider_str = node.get("provider", ModelProvider.OPENAI.value)
        try:
            provider = ModelProvider(provider_str)
        except ValueError:
            provider = ModelProvider.OPENAI

        model_name = node.get("model", "gpt-4o")
        max_tokens = int(node.get("max_tokens", 2000) or 2000)

        prompt_tokens = max_tokens // 2
        completion_tokens = max_tokens

        p_price, c_price = _get_price_per_token(provider, model_name)
        total += p_price * prompt_tokens + c_price * completion_tokens

    return float(round(total, 6))
