from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from ice_core.services.contracts import NetworkStorage

if TYPE_CHECKING:  # pragma: no cover – optional dependency
    import supabase

class SupabaseNetworkStorage(NetworkStorage):
    """Supabase-backed implementation of the *NetworkStorage* port.

    Parameters
    ----------
    client : supabase.Client
        Authenticated Supabase client.  The async client is recommended so we
        conform to repo rule 5 and avoid blocking the event loop.
    """

    def __init__(self, client: "supabase.Client") -> None:  # type: ignore[name-defined]
        self._client = client

    # ------------------------------------------------------------------
    # NetworkStorage implementation
    # ------------------------------------------------------------------

    async def get(self, spec_id: str) -> Optional[dict]:  # – simple CRUD
        resp = (
            await self._client.table("network_specs")
            .select("*")
            .eq("id", spec_id)
            .execute()
        )
        return resp.data[0] if resp.data else None

    async def put(self, spec_id: str, spec: dict) -> None:  # – simple CRUD
        await (
            self._client.table("network_specs")
            .upsert({**spec, "id": spec_id})
            .execute()
        )

    async def query(self, filter: str = "") -> List[dict]:  # – simple CRUD
        query_builder = self._client.table("network_specs").select("*")
        if filter:
            # Basic example using ILIKE for name filtering.
            query_builder = query_builder.ilike("name", f"%{filter}%")
        resp = await query_builder.execute()
        return resp.data or []
