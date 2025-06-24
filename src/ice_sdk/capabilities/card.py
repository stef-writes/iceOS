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

from typing import Any, Dict, Literal, Type

from pydantic import BaseModel

from ice_sdk.tools.base import BaseTool

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
    input_ports: Dict[str, str] | None = None
    output_ports: Dict[str, str] | None = None
    tags: list[str] = []
    version: str = "0.1.0"
    icon: str | None = None
    docs_url: str | None = None

    # ------------------------------------------------------------------
    # Factory helpers ---------------------------------------------------
    # ------------------------------------------------------------------

    @classmethod
    def from_tool_cls(cls, tool_cls: Type[BaseTool]) -> "CapabilityCard":
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
        ) 