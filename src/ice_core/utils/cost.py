"""Utility helpers for *predicting* chain execution cost.

Unlike `ice_sdk.providers.costs.calculate_cost`, this module does **not** need
actual token counts – it applies rough heuristics to a JSON Workflow spec so
operators can gauge budget before execution (e.g. `ice run-chain --estimate`).

Public API
~~~~~~~~~~
    estimate_chain_cost(chain_spec: dict) -> float
"""

from __future__ import annotations

from typing import Any, Dict

from ice_core.models.enums import ModelProvider
from ice_sdk.providers.costs import get_price_per_token

__all__: list[str] = ["estimate_chain_cost"]


def estimate_chain_cost(chain_spec: Dict[str, Any]) -> float:  # noqa: D401
    """Return rough USD cost for *chain_spec*.

    Heuristics:
    1. Iterate nodes; only consider types "ai" or "llm".
    2. For each node use `max_tokens` (default 2 000).
    3. Assume prompt_tokens = 0.5 × max_tokens, completion_tokens = max_tokens.
    4. Look-up per-token prices via :pymeth:`ice_sdk.providers.costs.get_price_per_token`.
    """

    total: float = 0.0

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

        p_price, c_price = get_price_per_token(provider, model_name)
        total += float(p_price * prompt_tokens + c_price * completion_tokens)

    return round(total, 6)
