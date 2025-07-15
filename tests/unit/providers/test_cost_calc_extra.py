from decimal import Decimal

from ice_sdk.models.config import ModelProvider
from ice_sdk.providers.costs import calculate_cost


def test_calculate_cost_zero_usage():
    """Zero tokens -> zero cost (regression guard)."""

    cost = calculate_cost(
        ModelProvider.OPENAI, "gpt-3.5-turbo", prompt_tokens=0, completion_tokens=0
    )
    assert cost == Decimal("0")
