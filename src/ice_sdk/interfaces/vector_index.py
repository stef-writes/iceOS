from __future__ import annotations

from typing import Any, Dict, List, Protocol, Tuple, runtime_checkable


@runtime_checkable
class IVectorIndex(Protocol):
    """Minimal async vector index contract."""

    async def upsert(
        self,
        scope: str,
        key: str,
        embedding: List[float],
        *,
        model_version: str,
        dedup: bool = False,
    ) -> None: ...

    async def query(
        self,
        scope: str,
        embedding: List[float],
        *,
        k: int = 5,
        filter: Dict[str, Any] | None = None,
    ) -> List[Tuple[str, float]]: ...
