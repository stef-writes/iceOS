"""Interfaces (Protocols) for guard-rail hooks that can be plugged into *ScriptChain*.

Guards are invoked *during* execution to decide whether the chain should
continue.  They receive the current metric/level information and must return
``True`` to allow execution to proceed or ``False`` to abort.
"""

from __future__ import annotations

from typing import Protocol


class TokenGuard(Protocol):
    """Decide whether execution can continue based on token usage.

    Args:
        total_tokens: Tokens consumed so far by the chain.
        ceiling: The configured ceiling (may be *None* for unlimited).

    Return ``True`` to continue, ``False`` to abort.
    """

    def __call__(self, total_tokens: int, ceiling: int | None) -> bool:  # noqa: D401
        ...  # pragma: no cover


class DepthGuard(Protocol):
    """Decide whether execution can continue at a given depth level."""

    def __call__(self, depth: int, ceiling: int | None) -> bool:  # noqa: D401
        ...  # pragma: no cover 