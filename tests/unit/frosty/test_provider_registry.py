from frosty.core import available_providers, get_provider
from frosty.core.providers.base import LLMProvider
import asyncio


def test_all_providers_implement_protocol() -> None:
    for name in available_providers():
        provider = get_provider(name)
        assert isinstance(provider.name, str)

        # Ensure complete is awaitable and returns string
        result = asyncio.run(provider.complete("test"))
        assert isinstance(result, str)