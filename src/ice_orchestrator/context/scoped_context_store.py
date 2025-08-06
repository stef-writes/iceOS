"""Scoped variant of :class:`ice_orchestrator.context.store.ContextStore`.

Keeps data isolated by prefixing every *node_id* with a caller-supplied
*scope* (commonly a tenant or workspace slug).  Drop-in replacement for
``ContextStore``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .store import ContextStore

__all__: list[str] = [
    "ScopedContextStore",
]


class ScopedContextStore(ContextStore):
    """ContextStore that namespaces keys inside a user-defined *scope*.

    Example
    -------
    >>> store = ScopedContextStore("tenant123")
    >>> store.set("node-a", {"foo": "bar"})  # internally stores under
    ...                                         # "tenant123:node-a"
    """

    def __init__(self, scope: str, *, context_store_path: Optional[str] = None):
        self._scope = scope
        super().__init__(context_store_path=context_store_path)

    # Internal ---------------------------------------------------------
    def _key(self, node_id: str) -> str:
        return f"{self._scope}:{node_id}"

    # Public API overrides --------------------------------------------
    def get(self, node_id: str) -> Any:  # type: ignore[override]
        return super().get(self._key(node_id))

    def set(  # type: ignore[override]
        self,
        node_id: str,
        context: Dict[str, Any],
        schema: Optional[Dict[str, str]] = None,
    ) -> None:
        super().set(self._key(node_id), context, schema=schema)

    def update(  # type: ignore[override]
        self,
        node_id: str,
        content: Any,
        execution_id: Optional[str] = None,
        schema: Optional[Dict[str, str]] = None,
    ) -> None:
        super().update(self._key(node_id), content, execution_id, schema)

    def clear(self, node_id: Optional[str] = None) -> None:  # type: ignore[override]
        if node_id is not None:
            super().clear(self._key(node_id))
        else:
            keys = [
                k
                for k in list(self.context_cache.keys())
                if k.startswith(f"{self._scope}:")
            ]
            for k in keys:
                super().clear(k)
