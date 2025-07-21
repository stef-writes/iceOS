from __future__ import annotations

from ice_sdk.models.node_models import NodeConfig, NodeExecutionResult


class TypeAwareRetry:
    def __init__(self, node: NodeConfig):
        self.node = node
        self.retry_policy = {
            "type_mismatch": {
                "max_attempts": 2,
                "corrective_action": self._fix_type_mismatch,
            }
        }

    async def execute(self, context: dict) -> NodeExecutionResult:
        # Placeholder stub – real implementation forthcoming
        from ice_sdk.models.node_models import NodeExecutionResult, NodeMetadata

        return NodeExecutionResult(
            success=True,
            output=context,  # echo back context
            metadata=NodeMetadata(node_id=self.node.id, node_type=str(self.node.type)),  # type: ignore[call-arg]
        )

    def _fix_type_mismatch(self, context: dict, error: Exception) -> dict:  # noqa: D401
        """Attempt to correct type mismatches – stub returns context unchanged."""
        return context


# ---------------------------------------------------------------------------
# Simple async retry decorator – limited subset used in unit tests
# ---------------------------------------------------------------------------

from functools import wraps
from typing import Callable, Coroutine, Type, Tuple


def async_retry(
    *,
    max_attempts: int = 3,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    log_retries: bool = False,
):
    """Lightweight asyncio-compatible retry decorator.

    Parameters
    ----------
    max_attempts
        Maximum attempts before giving up.
    retry_on
        Tuple of exception classes that trigger a retry.
    log_retries
        When *True*, print basic retry diagnostics (kept minimal to avoid
        introducing structured logging dependencies in the SDK layer).
    """

    def _decorator(fn: Callable[..., Coroutine]):  # type: ignore[type-arg]
        @wraps(fn)
        async def _wrapper(*args, **kwargs):  # type: ignore[no-self-use]
            attempt = 0
            last_exc: Exception | None = None
            while attempt < max_attempts:
                try:
                    return await fn(*args, **kwargs)
                except retry_on as exc:  # type: ignore[misc]
                    last_exc = exc
                    attempt += 1
                    if log_retries:
                        print(
                            f"Retry {attempt}/{max_attempts} for {fn.__name__}: {exc}"
                        )
                    if attempt >= max_attempts:
                        raise
        return _wrapper

    return _decorator
