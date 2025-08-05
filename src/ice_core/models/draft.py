from __future__ import annotations

"""Shared blueprint draft state models and stores.

Located in *ice_core* so both the API layer and authoring tools can depend on
it without violating layer-boundary rules (builder -> core, api -> core).
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple, TypedDict, cast

# Optional Redis dependency is only required if a Redis store is actually used.
try:
    import redis.asyncio as redis
except ModuleNotFoundError:  # pragma: no cover – optional dependency
    redis = None  # type: ignore

from ice_core.models.mcp import Blueprint

__all__ = [
    "DraftState",
    "DraftStore",
    "InMemoryDraftStore",
    "RedisDraftStore",
]


class _StatusDict(TypedDict, total=False):
    status: Dict[str, str]
    schema_rev: int


@dataclass
class DraftState:
    """State of an in-progress blueprint draft shown on the Canvas."""

    # Prompt / clarification history (oldest → newest)
    prompt_history: List[str] = field(default_factory=list)

    # Mermaid versions (ASCII string) aligned with prompt_history indexes
    mermaid_versions: List[str] = field(default_factory=list)

    # Node IDs that the *user* explicitly locked on the Canvas
    locked_nodes: List[str] = field(default_factory=list)

    # Node positions (x, y) recorded by the front-end Canvas
    node_positions: Dict[str, Tuple[int, int]] = field(default_factory=dict)

    # Draft nodes keyed by node_id – dict form allows O(1) look-ups
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # The most recent validated (partial) Blueprint, if any
    last_blueprint: Optional[Blueprint] = None

    # Interactive pipeline supplemental fields --------------------
    specification: Optional[str] = None
    mermaid_diagram: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    intent_data: Optional[Dict[str, Any]] = None
    plan_text: Optional[str] = None
    current_stage: Any = None  # PipelineStage but avoid circular import
    blueprint: Optional[Blueprint] = None

    # Arbitrary scratch-pad (includes a "status" dict by convention)
    meta: _StatusDict = field(default_factory=lambda: cast(_StatusDict, {"status": {}}))


class DraftStore(Protocol):
    """Persistence interface for DraftState (session-scoped, short-lived)."""

    async def load(self, session_id: str) -> Optional[DraftState]: ...

    async def save(self, session_id: str, state: DraftState) -> None: ...


class InMemoryDraftStore:
    """Process-local DraftStore – used in unit tests and dev CLI."""

    _store: Dict[str, DraftState] = {}

    async def load(self, session_id: str) -> Optional[DraftState]:  # noqa: D401
        return self._store.get(session_id)

    async def save(self, session_id: str, state: DraftState) -> None:  # noqa: D401
        # Shallow copy to avoid external mutation
        self._store[session_id] = state


# -------------------------- Optional Redis store -----------------------------


class RedisDraftStore(DraftStore):
    """Persist DraftState in Redis using JSON serialization."""

    def __init__(
        self,
        *,
        redis_url: str | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        if redis is None:
            raise RuntimeError(
                "redis[asyncio] package not installed – cannot use RedisDraftStore"
            )
        from typing import cast
        self._redis_url: str = cast(str, redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        _default_ttl = 60 * 60 * 24  # 24h
        self._ttl = ttl_seconds or int(os.getenv("DRAFTSTORE_TTL", str(_default_ttl)))
        # Redis client returns Any (no type hints); cast for mypy strict
        from typing import Callable, cast
        from_url_typed = cast(Callable[..., "redis.Redis"], redis.from_url)
        self._client: Any = from_url_typed(self._redis_url, decode_responses=True)

    # ----------------------------- helpers ---------------------------------
    def _key(self, session_id: str) -> str:  # noqa: D401 – small util
        return f"draft:{session_id}"

    # ----------------------------- DraftStore ------------------------------
    async def load(self, session_id: str) -> Optional[DraftState]:  # noqa: D401
        raw = await self._client.get(self._key(session_id))
        if raw is None:
            return None
        data = json.loads(raw)
        return DraftState(**data)  # type: ignore[arg-type]

    async def save(self, session_id: str, state: DraftState) -> None:  # noqa: D401
        data = json.dumps(state.__dict__, default=lambda o: o.__dict__)
        await self._client.set(self._key(session_id), data, ex=self._ttl)
