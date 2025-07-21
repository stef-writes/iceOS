"""Factory helper for building :class:`ice_orchestrator.workflow.Workflow` instances
from *NetworkSpec* YAML files.

Backward-compat helper retained — previously referred to *ScriptChain*.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:  # pragma: no cover
    from ice_orchestrator.workflow import Workflow

import yaml

from ice_orchestrator.core.chain_factory import ChainFactory
from ice_orchestrator.core.chain_registry import get_chain

# NOTE: use SDK models interface rather than importing from core
from ice_sdk.models.network import NetworkSpec


class NetworkFactory:  # – internal helper
    @staticmethod
    async def from_yaml(path: str | Path, **kwargs: Any) -> "Workflow":
        """Build a :class:`Workflow` from a *NetworkSpec* YAML file.

        Args:
            path (str | pathlib.Path): Filesystem location of the YAML spec.
            **kwargs: Keyword-arguments forwarded to `ChainFactory.from_dict`—
                e.g. `context_manager`, `callbacks`, etc.

        Returns:
            Workflow: A fully-initialised workflow ready for execution.

        Example:
            >>> chain = await NetworkFactory.from_yaml("specs/checkout.yaml")
            >>> await chain.execute()
        """

        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(path)

        data = yaml.safe_load(p.read_text())
        try:
            spec = NetworkSpec.model_validate(data)
        except Exception:
            # Legacy spec fallback ------------------------------------------------
            class _LegacySpec:  # minimal shim to satisfy attribute access
                def __init__(self, raw: dict):
                    self.nodes = raw.get("nodes", {})
                    self.metadata = raw.get("metadata", {})

            spec = _LegacySpec(data)  # type: ignore[assignment]

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

        metadata = getattr(spec, "metadata", {})
        payload: Dict[str, Any] = {
            "name": metadata.get("name", "legacy-network"),
            "description": metadata.get("description", ""),
            "version": metadata.get("version", "1.0.0"),
            "tags": metadata.get("tags", []),
            "nodes": node_payloads,
        }

        # comment for unused alias in postponed annotations

        chain_obj: Workflow = await ChainFactory.from_dict(
            payload, validate_outputs=False, **kwargs
        )
        return chain_obj

    # Convenience synchronous wrapper ---------------------------------------
    @staticmethod
    def build(path: str | Path, **kwargs: Any) -> "Workflow":
        """Synchronous convenience wrapper around `from_yaml`.

        This helper runs the async factory under the hood so callers in
        scripting contexts don’t have to manage an event-loop.

        Args:
            path (str | pathlib.Path): YAML file path.
            **kwargs: Same as `from_yaml`.

        Returns:
            Workflow: Parsed workflow instance.

        Example:
            >>> chain = NetworkFactory.build("spec.yaml")
            >>> result = chain.execute()  # blocks until finished
        """

        # comment

        async def _inner() -> "Workflow":
            return await NetworkFactory.from_yaml(path, **kwargs)

        return asyncio.run(_inner())
