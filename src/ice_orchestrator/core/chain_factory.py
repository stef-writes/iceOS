"""Factory for creating ScriptChain instances from JSON payloads.

Extracted from `Workflow` (formerly `ScriptChain`).  New code should import
`ice_orchestrator.workflow.Workflow`; this module still references
`ScriptChain` for backward-compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

if TYPE_CHECKING:  # pragma: no cover
    from ice_orchestrator.workflow import ScriptChain


class ChainFactory:  # noqa: D101 – internal utility
    """Factory for creating ScriptChain instances from JSON-compatible payloads."""

    @classmethod
    async def from_dict(
        cls,
        payload: Dict[str, Any],
        *,
        target_version: str = "1.0.0",
        **kwargs: Any,
    ) -> "ScriptChain":
        """Create a ScriptChain from JSON-compatible *payload*.

        Currently supports version "1.0.0" without migration.
        """

        # 1. Version check (no migration needed for current version) ------
        current_version: str = payload.get("version", "1.0.0")
        if current_version != target_version:
            raise ValueError(f"Version mismatch: {current_version} != {target_version}")

        # 2. Parse nodes --------------------------------------------------
        nodes_raw = payload.get("nodes", [])
        if not nodes_raw:
            raise ValueError("Workflow payload must contain 'nodes' key")

        # Discriminated union parsing (manual to avoid Annotated typing issues)
        from pydantic import BaseModel

        from ice_sdk.models.node_models import (
            LLMOperatorConfig,
            SkillNodeConfig,
            ConditionNodeConfig,
            NestedChainConfig,
        )

        _parser_map: Dict[str, type[BaseModel]] = {
            "ai": LLMOperatorConfig,  # legacy discriminator kept for B/C
            "llm": LLMOperatorConfig,
            "tool": SkillNodeConfig,  # legacy discriminator
            "skill": SkillNodeConfig,
            "condition": ConditionNodeConfig,
        }

        nodes: list[
            LLMOperatorConfig | SkillNodeConfig | ConditionNodeConfig | NestedChainConfig
        ] = []
        for nd in nodes_raw:
            node_type = nd.get("type")
            parser_cls = _parser_map.get(node_type)
            if parser_cls is None:
                raise ValueError(f"Unknown node type '{node_type}' in workflow spec")
            parsed_node = parser_cls.model_validate(nd)
            nodes.append(
                cast(
                    LLMOperatorConfig
                    | SkillNodeConfig
                    | ConditionNodeConfig
                    | NestedChainConfig,
                    parsed_node,
                )
            )

        # 3. Instantiate chain -------------------------------------------
        import hashlib
        import json

        from ice_orchestrator.workflow import Workflow
        from ice_sdk.models.node_models import ChainMetadata

        # Compute basic DAG statistics & topology hash ------------------
        node_count = len(nodes)
        edge_count = sum(len(getattr(n, "dependencies", [])) for n in nodes)

        # Deterministic hash of adjacency list (node id -> sorted deps)
        adjacency = {n.id: sorted(getattr(n, "dependencies", [])) for n in nodes}
        topology_hash = hashlib.sha256(
            json.dumps(adjacency, sort_keys=True).encode()
        ).hexdigest()

        chain_meta = ChainMetadata(
            chain_id=payload.get("chain_id", f"chain_{topology_hash[:8]}"),
            name=payload.get("name", "unnamed-chain"),
            version=payload.get("version", target_version),
            description=payload.get("description", ""),
            node_count=node_count,
            edge_count=edge_count,
            topology_hash=topology_hash,
            tags=payload.get("tags", []),
        )

        chain = Workflow(
            nodes=nodes,
            name=payload.get("name"),
            version=payload.get("version", target_version),
            **kwargs,
        )

        # Attach metadata for later dashboards / side-car emission
        setattr(chain, "metadata", chain_meta)

        return chain
