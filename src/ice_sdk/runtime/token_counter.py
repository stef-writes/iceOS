"""
Token counting utilities for different model providers (moved to ice_sdk.runtime).
"""

from typing import Dict, List

import tiktoken

from ice_sdk.models.config import ModelProvider

__all__ = ["TokenCounter"]


class TokenCounter:
    """Token counting utility for different model providers"""

    MODEL_ENCODINGS = {
        "openai": {
            "gpt-4": "cl100k_base",
            "gpt-4-turbo": "cl100k_base",
            "gpt-4-turbo-2024-04-09": "cl100k_base",
            "gpt-4-32k": "cl100k_base",
            "gpt-3.5-turbo": "cl100k_base",
        },
        "anthropic": {
            "claude-3-opus": "claude-3",
            "claude-3-sonnet": "claude-3",
            "claude-2": "claude-2",
        },
        "google": {"gemini-pro": "gemini", "gemini-ultra": "gemini"},
    }

    @classmethod
    def get_encoding_name(
        cls, model: str, provider: str | ModelProvider = "openai"
    ) -> str:
        provider_encodings = cls.MODEL_ENCODINGS.get(provider, {})
        encoding = provider_encodings.get(model)
        if not encoding:
            raise ValueError(
                f"No encoding found for model {model} from provider {provider}"
            )
        return encoding

    @classmethod
    def count_tokens(
        cls, text: str, model: str, provider: str | ModelProvider = "openai"
    ) -> int:
        if provider == "openai":
            try:
                encoding = tiktoken.get_encoding(cls.get_encoding_name(model, provider))
                return len(encoding.encode(text))
            except Exception as e:
                raise ValueError(
                    f"Error counting tokens for OpenAI model {model}: {str(e)}"
                )
        else:
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception as e:
                raise ValueError(
                    f"Error counting tokens for provider {provider} model {model}: {str(e)}"
                )

    @classmethod
    def count_message_tokens(
        cls,
        messages: List[Dict[str, str]],
        model: str,
        provider: str | ModelProvider = "openai",
    ) -> int:
        total_tokens = 0
        if provider == "openai":
            encoding = tiktoken.get_encoding(cls.get_encoding_name(model, provider))
            for message in messages:
                total_tokens += len(encoding.encode(message["role"]))
                total_tokens += len(encoding.encode(message["content"]))
                total_tokens += 4
            return total_tokens
        else:
            for message in messages:
                total_tokens += cls.count_tokens(message["content"], model, provider)
            return total_tokens

    @classmethod
    def estimate_tokens(
        cls, text: str, model: str, provider: str | ModelProvider = "openai"
    ) -> int:
        return len(text) // 4

    @classmethod
    def validate_token_limit(
        cls,
        text: str,
        max_tokens: int,
        model: str,
        provider: str | ModelProvider = "openai",
    ) -> bool:
        try:
            token_count = cls.count_tokens(text, model, provider)
            return token_count <= max_tokens
        except ValueError:
            return cls.estimate_tokens(text, model, provider) <= max_tokens
