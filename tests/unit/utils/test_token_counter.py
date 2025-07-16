from ice_sdk.models.config import ModelProvider
from ice_sdk.runtime.token_counter import TokenCounter


def test_estimate_tokens():
    text = "hello world" * 50
    assert (
        TokenCounter.estimate_tokens(
            text, model="gpt-4o", provider=ModelProvider.OPENAI
        )
        > 0
    )
