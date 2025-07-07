"""Factory helper for building ScriptChain instances from *NetworkSpec* YAML files."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

import yaml

from ice_orchestrator.core.chain_factory import ChainFactory
from ice_orchestrator.core.chain_registry import get_chain
from ice_sdk.models.network import NetworkSpec


class NetworkFactory:  # noqa: D101 – internal helper
    @staticmethod
    async def from_yaml(path: str | Path, **kwargs: Any):  # noqa: D401
        """Parse *path* and return a ready-to-run :class:`ScriptChain`."""

        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(path)

        data = yaml.safe_load(p.read_text())
        spec = NetworkSpec.model_validate(data)

        # ------------------------------------------------------------------
        # Convert node mapping → list with explicit "id" fields
        # ------------------------------------------------------------------
        node_payloads: List[Dict[str, Any]] = []
        for node_id, node_cfg in spec.nodes.items():
            node_cfg = dict(node_cfg)  # shallow copy
            node_cfg["id"] = node_id

            if node_cfg.get("type") == "nested_chain":
                chain_id = node_cfg.pop("chain_id", None)
                if not chain_id:
                    raise ValueError(
                        f"nested_chain node '{node_id}' missing 'chain_id'"
                    )
                child_chain = get_chain(chain_id)
                if child_chain is None:
                    raise ValueError(f"Chain '{chain_id}' not found in registry")
                node_cfg["chain"] = child_chain

            node_payloads.append(node_cfg)

        payload: Dict[str, Any] = {
            "name": spec.metadata.name,
            "description": spec.metadata.description or "",
            "version": spec.metadata.version,
            "tags": spec.metadata.tags,
            "nodes": node_payloads,
        }

        chain = await ChainFactory.from_dict(payload, **kwargs)
        return chain

    # Convenience synchronous wrapper ---------------------------------------
    @staticmethod
    def build(path: str | Path, **kwargs: Any):  # noqa: D401
        async def _inner():
            return await NetworkFactory.from_yaml(path, **kwargs)

        return asyncio.run(_inner())
