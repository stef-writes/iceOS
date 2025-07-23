from __future__ import annotations

import asyncio
from typing import Any, Dict

from pydantic import BaseModel

from ice_sdk.registry.chain import global_chain_registry


class ChainRequest(BaseModel):
    chain_name: str
    context: Dict[str, Any]


class ChainService:
    _registry = global_chain_registry  # simple alias

    def available_chains(self) -> list[str]:
        return sorted(name for name, _ in self._registry)

    async def run(self, request: ChainRequest):
        chain = self._registry.get(request.chain_name)
        run_fn = getattr(chain, "run")
        if not callable(run_fn):
            raise TypeError("Chain missing 'run' callable")

        if asyncio.iscoroutinefunction(run_fn):
            return await run_fn(request.context)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run_fn, request.context) 