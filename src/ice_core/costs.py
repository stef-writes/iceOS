"""Utility for looking-up model pricing and computing cost of a completion.

The tables reflect *per-token* prices in USD.  They are intentionally kept
in a single place so that future provider additions or price changes are a
simple data-edit, not a code change elsewhere in the SDK.

Price data taken from public pricing pages (May 2025).  Feel free to update.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Dict, Optional, Tuple

from ice_core.models import ModelProvider

# ----------------------------------------
# Per-token pricing tables ---------------------------------------------------
# ----------------------------------------
# Format:  {model_name: (prompt_price, completion_price)}  – prices in USD
# *prompt_price* applies to input / prompt tokens
# *completion_price* applies to output / completion tokens
#
# NOTE:  Use ``Decimal`` for currency math to avoid FP rounding errors.
# ----------------------------------------

_OPENAI_PRICES: Dict[str, Tuple[Decimal, Decimal]] = {
    #  ✅ Numbers copied from https://openai.com/pricing (2025-05-12)
    "gpt-4o": (Decimal("0.000005"), Decimal("0.000015")),
    "gpt-4o-mini": (Decimal("0.000003"), Decimal("0.000009")),
    "gpt-4-turbo": (Decimal("0.000010"), Decimal("0.000030")),
    "gpt-4": (Decimal("0.000030"), Decimal("0.000060")),
    "gpt-3.5-turbo": (Decimal("0.0000005"), Decimal("0.0000015")),
    "gpt-4-turbo-2024-04-09": (Decimal("0.000010"), Decimal("0.000030")),
}

# Mapping by provider --------------------------------------------------------
_PRICING_TABLE: Dict[ModelProvider, Dict[str, Tuple[Decimal, Decimal]]] = {
    ModelProvider.OPENAI: _OPENAI_PRICES,
    # Future providers can be added here, e.g. ModelProvider.ANTHROPIC: {...}
}

# ----------------------------------------
# Public helpers -------------------------------------------------------------
# ----------------------------------------

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

class TokenCostCalculator:
    """Calculator for token-based costs across different providers."""
    
    def __init__(self) -> None:
        pass
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: str = "openai"
    ) -> float:
        """Calculate cost for given token usage.
        
        Args:
            model: Model name (e.g., "gpt-4")
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
            provider: Provider name (e.g., "openai")
            
        Returns:
            Cost in USD as a float
        """
        try:
            # Map string provider to enum
            if isinstance(provider, str):
                provider_enum = ModelProvider(provider.lower())
            else:
                provider_enum = provider
                
            cost_decimal = calculate_cost(
                provider_enum, model, input_tokens, output_tokens
            )
            return float(cost_decimal)
        except (ValueError, KeyError):
            # Unknown provider/model - return zero cost
            return 0.0
    
    def get_model_pricing(self, provider: str, model: str) -> Tuple[float, float]:
        """Get per-token pricing for a model.
        
        Args:
            provider: Provider name  
            model: Model name
            
        Returns:
            Tuple of (prompt_price, completion_price) per token
        """
        try:
            provider_enum = ModelProvider(provider.lower())
            p_price, c_price = get_price_per_token(provider_enum, model)
            return float(p_price), float(c_price)
        except (ValueError, KeyError):
            return 0.0, 0.0


class CostTracker:
    """Tracks execution costs and time for chain execution"""

    def __init__(self) -> None:
        self._total_cost = Decimal("0")
        self._budget: Optional[Decimal] = None
        self._start_time: Optional[float] = None
        self._execution_time: Optional[float] = None

    def reset(self) -> None:
        """Reset tracker state"""
        self._total_cost = Decimal("0")
        self._budget = None
        self._start_time = None
        self._execution_time = None

    def set_budget(self, budget: float) -> None:
        """Set execution budget in USD"""
        self._budget = Decimal(str(budget))

    def add_cost(self, cost: Decimal) -> None:
        """Add cost to total"""
        self._total_cost += cost

        # Check budget limit
        if self._budget and self._total_cost > self._budget:
            raise RuntimeError(
                f"Budget exceeded: ${self._total_cost} > ${self._budget}"
            )

    def start_tracking(self) -> None:
        """Start execution time tracking"""
        self._start_time = time.time()

    def stop_tracking(self) -> None:
        """Stop execution time tracking"""
        if self._start_time:
            self._execution_time = time.time() - self._start_time

    def get_costs(self) -> Dict[str, float]:
        """Get cost summary"""
        costs: Dict[str, float] = {"total": float(self._total_cost)}
        if self._budget is not None:
            costs["budget"] = float(self._budget)
        return costs

    def get_execution_time(self) -> Optional[float]:
        """Get execution time in seconds"""
        return self._execution_time

    # ------------------------------------------------------------------
    # No-op *span* helpers used by ToolBase for cheap instrumentation.
    # ------------------------------------------------------------------

    @classmethod
    def start_span(cls, _name: str) -> None:  # – metric helper
        """Begin a logical cost span (no-op placeholder)."""

    @classmethod
    def end_span(cls, *, success: bool, error: str | None = None) -> None:
        """Finish a cost span – collects nothing for now."""


__all__ = [
    "get_price_per_token",
    "calculate_cost", 
    "CostTracker",
    "TokenCostCalculator",
]
