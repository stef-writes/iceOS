"""ChromaDBAdapter – in-process Chroma vector store implementation.

Phase-1 uses the default in-memory client – suitable for CI & small KBs.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Optional dependency: chromadb --------------------------------------------
# ---------------------------------------------------------------------------

try:
    import chromadb  # type: ignore

    _CHROMA_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover – CI/tests without the dep
    chromadb = None  # type: ignore
    _CHROMA_AVAILABLE = False

from ice_sdk.interfaces.vector_index import IVectorIndex

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------
_DEFAULT_DISTANCE = "cosine"


if _CHROMA_AVAILABLE:

    class ChromaDBAdapter(IVectorIndex):  # type: ignore[misc]
        """Async wrapper around ChromaDB Python client."""

        def __init__(
            self,
            *,
            distance_function: str = _DEFAULT_DISTANCE,
            storage_path: str | None = None,
        ) -> None:
            """Create an in-process Chroma client.

            Parameters
            ----------
            distance_function
                Metric for nearest-neighbour search.  Defaults to ``"cosine"``.
            storage_path
                If given (or if ``ICE_INDEX_STORAGE`` env var is set) the adapter
                will persist data to *that* directory using Chroma's
                ``duckdb+parquet`` backend.  If *None* it runs fully in-memory –
                ideal for unit tests and short-lived demo containers.
            """

            storage_dir: Optional[str] = storage_path or os.environ.get(
                "ICE_INDEX_STORAGE"
            )

            if storage_dir:
                expanded = str(Path(storage_dir).expanduser())
                Path(expanded).mkdir(parents=True, exist_ok=True)
                self._client = chromadb.Client.create(
                    settings={
                        "chroma_db_impl": "duckdb+parquet",
                        "persist_directory": expanded,
                    }
                )
            else:
                # Ephemeral in-memory instance – prior behaviour
                self._client = chromadb.Client()
            self._collections: Dict[str, chromadb.Collection] = {}
            self._distance = distance_function
            # Chroma uses thread blocking I/O; run in default executor
            self._loop = asyncio.get_event_loop()

        # ------------------------------------------------------------------
        # IVectorIndex compliance ------------------------------------------
        # ------------------------------------------------------------------
        async def upsert(
            self,
            scope: str,
            key: str,
            embedding: List[float],
            *,
            model_version: str,
            dedup: bool = False,
        ) -> None:  # noqa: D401 – interface
            collection = await self._get_collection(scope)

            # Optional dedup check – skip insert if id already exists
            if dedup:
                exists = await self._loop.run_in_executor(None, collection.peek, 1)
                if key in exists.get("ids", []):  # pragma: no cover – rare path
                    return

            # Chroma exposes sync API; wrap in executor
            await self._loop.run_in_executor(
                None,
                collection.upsert,
                [key],
                [embedding],
                [{"model": model_version}],
            )

        async def query(
            self,
            scope: str,
            embedding: List[float],
            *,
            k: int = 5,
            filter: Dict[str, Any] | None = None,
        ) -> List[Tuple[str, float]]:  # noqa: D401 – interface
            collection = await self._get_collection(scope)
            result = await self._loop.run_in_executor(
                None,
                collection.query,
                [embedding],
                k,
                filter,
            )
            ids = result["ids"][0]
            distances = result["distances"][0]
            return list(zip(ids, distances))

        # ------------------------------------------------------------------
        # Internal helpers --------------------------------------------------
        # ------------------------------------------------------------------
        async def _get_collection(
            self, scope: str
        ) -> chromadb.Collection:  # noqa: D401
            if scope in self._collections:
                return self._collections[scope]

            def _create() -> chromadb.Collection:  # noqa: D401
                return self._client.create_collection(
                    name=scope,
                    metadata={"hnsw:space": self._distance},
                )

            coll = await self._loop.run_in_executor(None, _create)
            self._collections[scope] = coll
            return coll

else:

    class ChromaDBAdapter(IVectorIndex):  # type: ignore[misc]
        """Fallback no-op adapter used when *chromadb* is unavailable.

        Stores embeddings in a simple in-memory dict so unit tests pass without
        the heavy dependency.  **Not** suitable for production scale/search
        quality.
        """

        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
            self._store: Dict[str, Dict[str, List[float]]] = {}

        async def upsert(
            self,
            scope: str,
            key: str,
            embedding: List[float],
            *,
            model_version: str,
            dedup: bool = False,
        ) -> None:  # noqa: D401
            self._store.setdefault(scope, {})[key] = embedding

        async def query(
            self,
            scope: str,
            embedding: List[float],
            *,
            k: int = 5,
            filter: Dict[str, Any] | None = None,
        ) -> List[Tuple[str, float]]:  # noqa: D401
            data = self._store.get(scope, {})
            if not data:
                return []

            # Naive L2 distance for tiny test vectors -------------------
            def _l2(a: List[float], b: List[float]) -> float:  # noqa: D401
                return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

            ranked = sorted(
                ((k, _l2(v, embedding)) for k, v in data.items()),
                key=lambda x: x[1],
            )
            return ranked[:k]
