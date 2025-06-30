"""
Token counting utilities for different model providers
"""

from typing import Dict, List

import tiktoken

from ice_sdk.models.config import ModelProvider


class TokenCounter:
    """Token counting utility for different model providers"""

    # Mapping of models to their encoding names
    MODEL_ENCODINGS = {
        "openai": {
            "gpt-4": "cl100k_base",
            "gpt-4-turbo": "cl100k_base",
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
    def get_encoding_name(cls, model: str, provider: str | ModelProvider = "openai") -> str:
        """Get the encoding name for a model.

        Args:
            model: Model name
            provider: Model provider

        Returns:
            Encoding name for the model

        Raises:
            ValueError: If model encoding is not found
        """
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
        """Count tokens in text for a specific model.

        Args:
            text: Text to count tokens in
            model: Model name
            provider: Model provider

        Returns:
            Number of tokens

        Raises:
            ValueError: If model encoding is not found
        """
        if provider == "openai":
            try:
                encoding = tiktoken.get_encoding(cls.get_encoding_name(model, provider))
                return len(encoding.encode(text))
            except Exception as e:
                raise ValueError(
                    f"Error counting tokens for OpenAI model {model}: {str(e)}"
                )
        elif provider == "anthropic":
            # Anthropic uses a similar tokenizer to GPT-3
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception as e:
                raise ValueError(
                    f"Error counting tokens for Anthropic model {model}: {str(e)}"
                )
        elif provider == "google":
            # Google's tokenizer is similar to GPT-3
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception as e:
                raise ValueError(
                    f"Error counting tokens for Google model {model}: {str(e)}"
                )
        elif provider == "custom":
            # For custom providers, use GPT-3 tokenizer as a fallback
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception as e:
                raise ValueError(
                    f"Error counting tokens for custom model {model}: {str(e)}"
                )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @classmethod
    def count_message_tokens(
        cls,
        messages: List[Dict[str, str]],
        model: str,
        provider: str | ModelProvider = "openai",
    ) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name
            provider: Model provider

        Returns:
            Total number of tokens

        Raises:
            ValueError: If model encoding is not found
        """
        total_tokens = 0

        if provider == "openai":
            # OpenAI's token counting includes special tokens and formatting
            try:
                encoding = tiktoken.get_encoding(cls.get_encoding_name(model, provider))
                for message in messages:
                    # Add tokens for role and content
                    total_tokens += len(encoding.encode(message["role"]))
                    total_tokens += len(encoding.encode(message["content"]))
                    # Add tokens for message formatting
                    total_tokens += 4  # Special tokens for message boundaries
                return total_tokens
            except Exception as e:
                raise ValueError(
                    f"Error counting message tokens for OpenAI model {model}: {str(e)}"
                )
        else:
            # For other providers, use a simpler counting method
            for message in messages:
                total_tokens += cls.count_tokens(message["content"], model, provider)
            return total_tokens

    @classmethod
    def estimate_tokens(
        cls, text: str, model: str, provider: str | ModelProvider = "openai"
    ) -> int:
        """Estimate tokens in text using a fast approximation.

        This is useful for quick estimates when exact counting is not critical.

        Args:
            text: Text to estimate tokens in
            model: Model name
            provider: Model provider

        Returns:
            Estimated number of tokens
        """
        # Average characters per token is roughly 4 for most models
        return len(text) // 4

    @classmethod
    def validate_token_limit(
        cls, text: str, max_tokens: int, model: str, provider: str | ModelProvider = "openai"
    ) -> bool:
        """Validate if text is within token limit.

        Args:
            text: Text to validate
            max_tokens: Maximum allowed tokens
            model: Model name
            provider: Model provider

        Returns:
            True if within limit, False otherwise
        """
        try:
            token_count = cls.count_tokens(text, model, provider)
            return token_count <= max_tokens
        except ValueError:
            # If token counting fails, use estimation
            return cls.estimate_tokens(text, model, provider) <= max_tokens
