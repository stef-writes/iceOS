from ice_sdk.utils.token_counter import TokenCounter
from ice_sdk.models.config import ModelProvider


def test_estimate_tokens():
    text = "hello world" * 50
    assert TokenCounter.estimate_tokens(text, model="gpt-4o", provider=ModelProvider.OPENAI) > 0 