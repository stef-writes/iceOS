import logging

from openai import APIError, RateLimitError, Timeout

logger = logging.getLogger(__name__)


class OpenAIErrorHandler:
    """Centralized error handling for OpenAI API calls"""

    @classmethod
    def classify_error(cls, error: Exception) -> str:
        error_map = {
            APIError: "APIError",
            RateLimitError: "RateLimitError",
            Timeout: "TimeoutError",
        }
        error_message = str(error).lower()
        if "api key" in error_message or "authentication" in error_message:
            return "AuthenticationError"
        elif "rate limit" in error_message:
            return "RateLimitError"
        elif "timeout" in error_message:
            return "TimeoutError"
        return error_map.get(type(error), "UnknownError")

    @classmethod
    def format_error_message(cls, error: Exception) -> str:
        error_type = cls.classify_error(error)
        if error_type == "APIError":
            return "API service unavailable. Please try again later."
        elif error_type == "RateLimitError":
            return "Rate limit exceeded. Please adjust your request rate."
        elif error_type == "TimeoutError":
            return "Request timed out. Please try again."
        elif error_type == "AuthenticationError":
            return "Authentication failed. Please check your API key."
        return str(error)
