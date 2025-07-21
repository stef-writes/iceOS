from __future__ import annotations

from typing import List, Optional

from ice_core.exceptions import SpecConflictError
from ice_core.services.contracts import NetworkStorage
from ice_sdk.models.network import NetworkSpec, NetworkValidationError
from ice_sdk.utils.retry import async_retry


class NetworkService:
    """Business logic for CRUD operations on :class:`NetworkSpec`.

    This implementation was relocated from *ice_orchestrator* to the SDK layer
    so that API endpoints can depend on it without violating layer boundaries.
    It remains transport-agnostic; persistence is delegated to a
    :class:`NetworkStorage` backend supplied via the constructor.
    """

    def __init__(self, storage: Optional[NetworkStorage] = None):
        if storage is None:
            # Lightweight fallback so that smoke tests do not require Supabase.
            class _InMemoryStore(NetworkStorage):
                def __init__(self) -> None:
                    self._data: dict[str, dict] = {}

                async def get(self, spec_id: str) -> Optional[dict]:
                    return self._data.get(spec_id)

                async def put(self, spec_id: str, spec: dict) -> None:
                    self._data[spec_id] = spec

                async def query(self, filter: str = "") -> List[dict]:
                    if not filter:
                        return list(self._data.values())
                    return [v for v in self._data.values() if filter in v.get("name", "")]  # type: ignore[arg-type]

            storage = _InMemoryStore()

        self._storage: NetworkStorage = storage

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------

    @async_retry(
        max_attempts=3,
        retry_on=(NetworkValidationError, SpecConflictError),
        log_retries=True,
    )
    async def create_network_spec(self, spec: NetworkSpec) -> str:
        """Validate and persist a new NetworkSpec, returning its ID."""

        spec.validate()

        existing = await self._storage.get(spec.id)
        if existing:
            raise SpecConflictError(spec.id)

        await self._storage.put(spec.id, spec.model_dump())
        return spec.id

    async def list_network_specs(self, filter: str = "") -> list[NetworkSpec]:
        """Return NetworkSpec objects matching *filter* (simple contains)."""

        raw_specs = await self._storage.query(filter)
        return [NetworkSpec(**s) for s in raw_specs]
