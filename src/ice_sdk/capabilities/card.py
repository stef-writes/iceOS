"""Unified metadata representation for discoverable *capabilities* (tools, agents, ai-nodes, …).

The initial implementation focuses on *tool* classes because they already expose
rich metadata such as ``name``, ``description`` and a JSON-schema for
parameters.  The design intentionally leaves room for other capability kinds so
future work can generate cards from *AiNode* & *Agent* templates or YAML files.

Why introduce this module now?
--------------------------------
1. It revives the archived "Capability Card" concept in a backend-friendly way.
2. Allows both CLIs and UIs to consume a single, structured object when they
   need to list/search capabilities.
3. Keeps **all** metadata in code — no duplication between runtime structs and
   documentation specs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Literal, Type

from pydantic import BaseModel, Field

from ice_sdk.skills import SkillBase

# Type-checking imports ------------------------------------------------------
if TYPE_CHECKING:  # pragma: no cover – import only for type checkers
    from ice_sdk.models.node_models import ChainMetadata, LLMOperatorConfig

# ---------------------------------------------------------------------------
# Public model ----------------------------------------------------------------
# ---------------------------------------------------------------------------

KindLiteral = Literal["tool", "ai_node", "agent", "other"]


class CapabilityCard(BaseModel):
    """Machine-readable description of a reusable capability.

    Attributes
    ----------
    id
        Unique slug (e.g. ``"web_search"``).
    kind
        The category of capability (``"tool"`` | ``"ai_node"`` | ``"agent"`` | …).
    name
        Human-readable name shown in UIs.
    description
        Short summary.
    parameters_schema
        JSON-schema for input parameters (only present for *tools* for now).
    input_ports / output_ports
        Named ports for nodes/agents.  Not used by tools but included to keep
        the schema stable across kinds.
    tags
        Free-form labels for search & grouping.
    version
        SemVer string – defaults to ``"0.1.0"`` if the source object does not
        expose its own version.
    icon / docs_url
        Optional UI niceties.
    """

    id: str
    kind: KindLiteral = "tool"
    name: str
    description: str
    parameters_schema: Dict[str, Any] | None = None
    input_ports: Dict[str, Any] | None = None
    output_ports: Dict[str, Any] | None = None
    tags: list[str] = []
    version: str = "0.1.0"
    icon: str | None = None
    docs_url: str | None = None

    # ------------------------------------------------------------------
    # Copilot-friendly extras -------------------------------------------
    # ------------------------------------------------------------------

    purpose: str | None = None
    examples: list[Dict[str, Any]] | None = None

    # Copilot planning aids ---------------------------------------------------
    complexity: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Rough cost / latency bucket (1 = trivial, 5 = expensive)",
    )
    required_tools: list[str] | None = None
    output_schema: Dict[str, Any] | None = None
    embedding: list[float] | None = None  # Sentence embedding of purpose+desc
    risk_level: Literal["low", "medium", "high"] | None = None

    # ------------------------------------------------------------------
    # Factory helpers ---------------------------------------------------
    # ------------------------------------------------------------------

    @classmethod
    def from_tool_cls(cls, tool_cls: Type[SkillBase]) -> "CapabilityCard":
        """Create a *CapabilityCard* from a ``BaseTool`` subclass."""

        return cls(
            id=tool_cls.name,
            kind="tool",
            name=getattr(tool_cls, "name", tool_cls.__name__),
            description=getattr(tool_cls, "description", ""),
            parameters_schema=getattr(tool_cls, "parameters_schema", None),
            output_ports=getattr(tool_cls, "output_schema", None),
            tags=getattr(tool_cls, "tags", []),
            version=getattr(tool_cls, "__version__", "0.1.0"),
            purpose=getattr(tool_cls, "purpose", None),
            examples=getattr(tool_cls, "examples", None),
            complexity=getattr(tool_cls, "complexity", None),
            output_schema=getattr(tool_cls, "output_schema", None),
        )

    # ------------------------------------------------------------------
    # Node/chain helpers -------------------------------------------------
    # ------------------------------------------------------------------

    @classmethod
    def from_ai_node_cfg(cls, node_cfg: "LLMOperatorConfig") -> "CapabilityCard":
        """Build a card from an :class:`LLMOperatorConfig`."""

        # Avoid heavy dependencies – import lazily ---------------------
        from ice_sdk.models.node_models import (  # noqa: WPS433 – runtime import
            LLMOperatorConfig,
        )

        assert isinstance(node_cfg, LLMOperatorConfig), "Expected LLMOperatorConfig"

        metadata = node_cfg.metadata or None

        return cls(
            id=node_cfg.id,
            kind="ai_node",
            name=node_cfg.name or node_cfg.id,
            description=(metadata.description or "" if metadata else ""),
            purpose=(metadata.description if metadata else None),
            tags=(metadata.tags if metadata else []),
            required_tools=node_cfg.allowed_tools,
            output_schema=(
                node_cfg.output_schema
                if isinstance(node_cfg.output_schema, dict)
                else None
            ),
            examples=None,
        )

    @classmethod
    def from_chain_metadata(cls, chain_meta: "ChainMetadata") -> "CapabilityCard":
        """Generate a card from :class:`ChainMetadata`."""

        from ice_sdk.models.node_models import (  # noqa: WPS433 – runtime import
            ChainMetadata,
        )

        assert isinstance(chain_meta, ChainMetadata)

        return cls(
            id=chain_meta.chain_id,
            kind="other",
            name=chain_meta.name,
            description=chain_meta.description,
            tags=chain_meta.tags,
            complexity=None,
            examples=None,
            purpose="Reusable workflow",
        )
