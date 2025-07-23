from __future__ import annotations

"""AgentService – runtime facade for executing agents by name.

This mirrors :pymod:`ice_sdk.tools.service` so orchestration layers can treat
agents symmetrically with tools.
"""

import asyncio
import importlib
import inspect
from typing import Any, Dict, List

from pydantic import BaseModel

from ice_sdk.registry.agent import global_agent_registry


class AgentRequest(BaseModel):
    agent_name: str
    inputs: Dict[str, Any]
    context: Dict[str, Any] | None = None  # Reserved for future extensions


class AgentService:
    """Thin compatibility layer – stateless wrapper around *Agent* objects."""

    _registry: Dict[str, Any] = {}

    def __init__(self) -> None:
        # 1. Snapshot already-registered agents ---------------------------
        for name, agent in global_agent_registry:
            self._registry.setdefault(name, agent)

        # 2. Discover entry-points ---------------------------------------
        try:
            from importlib.metadata import entry_points, PackageNotFoundError

            eps = entry_points(group="ice_sdk.agents")  # type: ignore[arg-type]
            for ep in eps:
                try:
                    agent_obj = ep.load()  # Expect *instance* or class
                    if inspect.isclass(agent_obj):
                        agent_obj = agent_obj()  # type: ignore[operator]
                    name = getattr(agent_obj, "name", ep.name)
                    self._registry.setdefault(name, agent_obj)
                except Exception:
                    continue
        except Exception:
            pass  # pragma: no cover – best-effort discovery

        # 3. Module walk fallback (mirrors ToolService) -------------------
        try:
            import pkgutil
            from ice_sdk.agents import __path__ as root_paths  # type: ignore[attr-defined]

            for finder, mod_name, _ in pkgutil.walk_packages(root_paths, prefix="ice_sdk.agents."):
                try:
                    mod = importlib.import_module(mod_name)
                    for obj in mod.__dict__.values():
                        if inspect.isclass(obj) and hasattr(obj, "execute"):
                            instance = obj()
                            name = getattr(instance, "name", obj.__name__)
                            self._registry.setdefault(name, instance)
                except Exception:
                    continue
        except ModuleNotFoundError:
            pass

    # ------------------------------------------------------------------ API helpers
    def available_agents(self) -> list[str]:
        return sorted(self._registry.keys())

    async def execute(self, request: AgentRequest) -> Any:
        agent_obj = self._registry.get(request.agent_name)
        if agent_obj is None:
            # Fallback – snapshot global registry in case new agents were added after instantiation
            try:
                agent_obj = global_agent_registry.get(request.agent_name)
                self._registry[request.agent_name] = agent_obj  # cache
            except Exception as exc:
                raise ValueError(f"Agent '{request.agent_name}' not registered") from exc

        exec_fn = getattr(agent_obj, "execute")
        if inspect.iscoroutinefunction(exec_fn):
            return await exec_fn(request.inputs)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, exec_fn, request.inputs) 