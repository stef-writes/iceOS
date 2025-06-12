"""
Token tracking and cost calculation utilities
"""

import functools
import time
from contextlib import contextmanager
from typing import Awaitable, Callable, Dict, TypeVar

T = TypeVar("T")


@contextmanager
def track_token_usage():
    """Context manager for tracking OpenAI token usage"""

    class TokenTracker:
        def __init__(self):
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.total_cost = 0.0
            self.start_time = time.time()

        def update(self, response: Dict):
            """Update metrics from OpenAI response"""
            usage = response.get("usage", {})
            self.prompt_tokens += usage.get("prompt_tokens", 0)
            self.completion_tokens += usage.get("completion_tokens", 0)
            self._calculate_cost()

        def _calculate_cost(self):
            """Estimate costs based on GPT-4 pricing"""
            self.total_cost += (self.prompt_tokens / 1000) * 0.03 + (
                self.completion_tokens / 1000
            ) * 0.06

    tracker = TokenTracker()
    try:
        yield tracker
    finally:
        duration = time.time() - tracker.start_time
        print(f"Execution took {duration:.2f}s")
        print(f"Total cost: ${tracker.total_cost:.4f}")


def track_usage(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """
    Decorator to track token usage for node execution.

    This decorator centralizes token usage tracking by:
    1. Capturing the result of the decorated function
    2. Extracting usage information from the result
    3. Updating the context manager with the usage data

    Args:
        func: The async function to decorate

    Returns:
        The decorated function
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get the context manager from the first argument (self)
        # This assumes the first argument is the node instance
        node = args[0]
        ctx = getattr(node, "context", None)

        # Execute the original function
        result = await func(*args, **kwargs)

        # If we have a context manager and the result has usage data, track it
        if ctx and hasattr(result, "usage") and result.usage:
            # Update the context with usage information
            ctx.track_usage(result.usage)

        return result

    return wrapper
