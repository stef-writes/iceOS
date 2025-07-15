"""Transaction state machine stubs for contract tests."""

from __future__ import annotations

from enum import Enum

__all__ = ["TxState", "Transaction"]


class TxState(str, Enum):  # noqa: D101 – stub enum
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Transaction:  # noqa: D101 – stub class
    def __init__(self, tx_id: str) -> None:
        self.id = tx_id
        self.state = TxState.PENDING

    async def run(self) -> None:  # noqa: D401 – stub
        self.state = TxState.COMPLETED
        return None
