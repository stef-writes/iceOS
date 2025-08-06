from __future__ import annotations

"""High-level network execution API exposed by the *SDK* layer.

This thin wrapper delegates to the concrete ``NetworkCoordinator`` registered
by the orchestrator in :pyfunc:`ice_orchestrator.initialize_orchestrator`.
It exists so that application code (or Frosty) can execute a network manifest
without importing the orchestrator package directly, preserving the onion/
layer boundaries.
"""

from pathlib import Path
from typing import Any, Dict, List

from ice_core.protocols.runtime_factories import NetworkCoordinatorFactory
from ice_core.runtime import network_coordinator_factory

__all__ = ["NetworkService"]


# ---------------------------------------------------------------------------
# Public facade
# ---------------------------------------------------------------------------


class NetworkService:
    """Public façade for loading & executing network manifests."""

    def __init__(self) -> None:  # noqa: D401 – simple init
        self._coordinator_cls: NetworkCoordinatorFactory | None = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        if network_coordinator_factory is None:
            raise RuntimeError(
                "`network_coordinator_factory` not set. The orchestrator layer must assign "
                "ice_core.runtime.network_coordinator_factory at start-up."
            )
        self._coordinator_cls = network_coordinator_factory  # type: ignore[assignment]
        self._initialized = True

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------

    async def execute(
        self,
        manifest_path: str | Path,
        *,
        scheduled: bool = False,
        loop_forever: bool = False,
    ) -> Dict[str, Any]:
        """Execute *manifest_path*.

        If *scheduled* is True, cron schedules inside the manifest are honoured.
        When *loop_forever* is also True, this call never returns (until
        cancelled).  Otherwise, it executes any due schedules **once**.
        """
        self._ensure_initialized()
        if self._coordinator_cls is None:
            raise RuntimeError("NetworkCoordinator not registered")
        coord = self._coordinator_cls.from_file(Path(manifest_path))  # type: ignore[arg-type]
        if scheduled:
            # Respect schedules
            await coord.execute_scheduled(loop_forever=loop_forever)
            return {}
        # One-off execution
        result = await coord.execute()
        return result if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Legacy spec CRUD stubs – no-op for now
    # ------------------------------------------------------------------

    async def create_network_spec(
        self, spec: Dict[str, Any]
    ) -> str:  # pragma: no cover
        """Stub to satisfy older API layers – returns fake ID."""
        import uuid

        return str(uuid.uuid4())

    async def list_network_specs(
        self, filter: str = ""
    ) -> List[Dict[str, Any]]:  # pragma: no cover
        return []
