from decimal import Decimal

from ice_sdk.models.config import ModelProvider
from ice_sdk.providers.costs import calculate_cost


def test_calculate_cost_openai_gpt4o():
    cost = calculate_cost(
        ModelProvider.OPENAI, "gpt-4o", prompt_tokens=1000, completion_tokens=500
    )
    # 1000*0.000005 + 500*0.000015 = 0.0125 USD
    assert cost == Decimal("0.0125")


# ---------------------------------------------------------------------------
# Unknown model handling -----------------------------------------------------
# ---------------------------------------------------------------------------


def test_calculate_cost_unknown_model_returns_zero():
    """Unknown (provider, model) pair should return zero cost instead of raising."""
    cost = calculate_cost(
        ModelProvider.OPENAI,
        "non-existent-model",
        prompt_tokens=10,
        completion_tokens=5,
    )
    assert cost == Decimal("0")
