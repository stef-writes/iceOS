"""Hybrid embedder – local MiniLM first, cloud providers as fallback.

Usage::
    >>> from ice_sdk.providers.embedding import get_embedder
    >>> emb = await get_embedder().embed("hello world")
"""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import List

from sentence_transformers import SentenceTransformer  # type: ignore

from ice_sdk.interfaces.embedder import IEmbedder
from ice_sdk.models.embedding import DEFAULT_DIM, Embedding
from ice_sdk.providers.budget_enforcer import BudgetEnforcer

# ---------------------------------------------------------------------------
# Constants ------------------------------------------------------------------
# ---------------------------------------------------------------------------
_LOCAL_MODEL_NAME = "all-MiniLM-L6-v2"
_LOCAL_MODEL_VERSION = f"sentence-transformers::{_LOCAL_MODEL_NAME}"

# Simple cost map – update when integrating real price sheets --------------
_PROVIDER_COST: dict[str, float] = {
    "local": 0.0,
    "titan": 0.0004,  # per 1 K chars – illustrative only
    "cohere": 0.0005,
    "openai": 0.0002,
}


class _StubRemoteProvider:  # noqa: D401 – internal helper
    """Very light stub standing in for real remote embed API."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.version = f"{name}-v1"

    def estimate_cost(self, text: str) -> float:  # noqa: D401
        return _PROVIDER_COST.get(self.name, 0.0005) * max(len(text) / 1000, 1)

    async def embed(self, text: str) -> List[float]:  # noqa: D401
        # In real impl, call remote API here.
        # For now, reuse local MiniLM but add small noise so tests can detect fallback.
        await asyncio.sleep(0.01)  # simulate network latency
        model = await _get_local_model()
        local_vec_any = await asyncio.get_event_loop().run_in_executor(
            _THREAD_POOL, model.encode, text
        )
        local_vec: List[float] = list(local_vec_any)  # type: ignore[arg-type]
        # Perturb first dim slightly to emulate different provider
        if local_vec:
            local_vec[0] += 0.001
        return local_vec


# Singleton local model loaded lazily ---------------------------------------
_LOCAL_MODEL: SentenceTransformer | None = None
_MODEL_LOCK = asyncio.Lock()
_THREAD_POOL = ThreadPoolExecutor(max_workers=1)


async def _get_local_model() -> SentenceTransformer:  # noqa: D401 – helper
    global _LOCAL_MODEL  # pylint: disable=global-statement
    async with _MODEL_LOCK:
        if _LOCAL_MODEL is None:
            # Load in threadpool to avoid blocking event loop
            _LOCAL_MODEL = await asyncio.get_event_loop().run_in_executor(
                _THREAD_POOL, SentenceTransformer, _LOCAL_MODEL_NAME
            )
        return _LOCAL_MODEL


class HybridEmbedder(IEmbedder):
    """Embedder that routes to local model first, then provider list."""

    def __init__(self, providers: list[str] | None = None) -> None:
        # Allow env override e.g. ICE_EMBED_ROUTER="local,openai"
        if not providers:
            env_router = os.getenv("ICE_EMBED_ROUTER")
            if env_router:
                providers = [p.strip() for p in env_router.split(",") if p.strip()]
        self._router_order = providers or ["local", "titan", "cohere", "openai"]
        # Build provider objects lazily – local handled separately
        self._remote_providers = {
            name: _StubRemoteProvider(name)
            for name in self._router_order
            if name != "local"
        }
        self._budget = BudgetEnforcer()

    # ------------------------------------------------------------------
    # IEmbedder compliance ---------------------------------------------
    # ------------------------------------------------------------------
    async def embed(self, text: str) -> Embedding:  # noqa: D401 – interface
        # 1. Try local model (free, fastest)
        if "local" in self._router_order:
            vec = await self._local_encode(text)
            return Embedding(vector=vec, model_version=_LOCAL_MODEL_VERSION)

        # 2. Iterate remote providers ---------------------------------
        for name in self._router_order:
            if name == "local":
                continue
            provider = self._remote_providers[name]
            cost = provider.estimate_cost(text)
            self._budget.register_llm_call(cost)
            try:
                remote_vec = await provider.embed(text)
                padded = self._pad_or_truncate(remote_vec)
                return Embedding(vector=padded, model_version=provider.version)
            except (
                Exception
            ):  # pragma: no cover – stub; real impl catches ProviderError
                continue

        raise RuntimeError("All embed providers failed")

    def estimate_cost(self, text: str) -> float:  # noqa: D401 – interface
        # Cost for first successful provider in router order
        for name in self._router_order:
            if name == "local":
                return 0.0
            provider = self._remote_providers[name]
            return provider.estimate_cost(text)
        return 0.0

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------
    @staticmethod
    def _pad_or_truncate(vec: List[float]) -> List[float]:  # noqa: D401
        if len(vec) < DEFAULT_DIM:
            return vec + [0.0] * (DEFAULT_DIM - len(vec))
        if len(vec) > DEFAULT_DIM:
            return vec[:DEFAULT_DIM]
        return vec

    async def _local_encode(self, text: str) -> List[float]:  # noqa: D401
        # Load model with 5-second timeout; otherwise treat as failure and let router fall back
        try:
            # Measure load latency for potential future telemetry
            start = perf_counter()
            model = await asyncio.wait_for(_get_local_model(), timeout=5.0)
            _ = (perf_counter() - start) * 1000  # ignore for now
        except asyncio.TimeoutError:  # pragma: no cover – network / cold path
            raise RuntimeError("local model load timeout")

        vec_any = await asyncio.get_event_loop().run_in_executor(
            _THREAD_POOL, model.encode, text
        )
        vec: List[float] = list(vec_any)  # type: ignore[arg-type]
        return self._pad_or_truncate(vec)

    # ------------------------------------------------------------------
    # Extra helpers -----------------------------------------------------
    # ------------------------------------------------------------------

    def estimate_latency(self, text: str) -> float:  # noqa: D401 – ms estimate
        """Rough wall-time estimate (ms) for embedding *text* via first router hop."""

        if self._router_order[0] == "local":
            # Heuristic: MiniLM ~1.5ms per 100 tokens on M1.  Cap at 1000ms.
            return min(len(text) / 100 * 1.5, 1000.0)
        # Remote provider – assume 300ms network + 50ms processing
        return 350.0
