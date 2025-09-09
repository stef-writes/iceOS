"""Node catalog endpoints for studio/copilot consumption.

Provides typed metadata for available nodes with schemas where applicable.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field


class UIHints(BaseModel):
    """Optional UI rendering hints for studio forms."""

    widget: str | None = Field(default=None, description="Preferred widget type")
    placeholder: str | None = None
    enum: List[str] | None = None
    step: float | None = None


class ToolInfo(BaseModel):
    """Catalog entry for a Tool node.

    Attributes
    ----------
    name : str
        Registry name of the tool factory.
    input_schema : dict[str, Any]
        JSON Schema describing expected inputs.
    output_schema : dict[str, Any]
        JSON Schema describing outputs.
    ui_hints : dict[str, UIHints] | None
        Optional mapping of field name to UI hints.
    examples : list[dict[str, Any]] | None
        Example argument objects usable in studio.
    """

    name: str = Field(..., description="Registry name of the tool factory")
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    ui_hints: Dict[str, UIHints] | None = None
    examples: List[Dict[str, Any]] | None = None


class NodeCatalog(BaseModel):
    """High-level node catalog for authoring UIs and copilots."""

    tools: List[ToolInfo] = Field(default_factory=list)
    agents: List[str] = Field(default_factory=list)
    workflows: List[str] = Field(default_factory=list)
    chains: List[str] = Field(default_factory=list)


router = APIRouter(prefix="/api/v1/meta", tags=["discovery", "catalog"])


@router.get("/nodes", response_model=NodeCatalog)
async def list_node_catalog() -> NodeCatalog:  # noqa: D401
    """Return catalog of nodes with schemas for tools.

    Notes
    -----
    - Tool schemas are discovered from the registered tool factories.
    - Other node categories are listed by name at this tier (schemas are
      typically resolved at compile-time or via specialized endpoints).
    """

    from ice_api.security import is_tool_allowed
    from ice_core.models import NodeType
    from ice_core.registry import global_agent_registry, global_chain_registry, registry
    from ice_core.utils.node_conversion import discover_tool_schemas

    # Tools with schemas
    tools: List[ToolInfo] = []
    for name in registry.list_tools():
        if not is_tool_allowed(name):
            continue
        try:
            input_schema, output_schema = discover_tool_schemas(name)
        except Exception:
            # Be resilient – provide empty schemas if discovery fails
            input_schema, output_schema = (
                {"type": "object", "properties": {}},
                {
                    "type": "object",
                    "properties": {},
                },
            )
        # Minimal automatic UI hints: map enum and numeric ranges if present
        hints: Dict[str, UIHints] = {}
        props = (
            input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
        )
        for field, spec in props.items():
            if not isinstance(spec, dict):
                continue
            hint = UIHints()
            if "enum" in spec:
                hint.enum = [str(v) for v in spec.get("enum", [])]
                hint.widget = hint.widget or "select"
            if spec.get("type") in {"number", "integer"}:
                hint.widget = hint.widget or "number"
                if "multipleOf" in spec:
                    hint.step = float(spec["multipleOf"])  # best-effort
            if "examples" in spec and isinstance(spec["examples"], list):
                # we attach examples at top-level below; keep per-field placeholder if available
                if spec["examples"]:
                    hint.placeholder = str(spec["examples"][0])
            if any([hint.widget, hint.placeholder, hint.enum, hint.step]):
                hints[field] = hint

        examples: List[Dict[str, Any]] | None = None
        ex_vals = (
            input_schema.get("examples") if isinstance(input_schema, dict) else None
        )
        if isinstance(ex_vals, list) and ex_vals and isinstance(ex_vals[0], dict):
            examples = ex_vals  # type: ignore[assignment]

        tools.append(
            ToolInfo(
                name=name,
                input_schema=input_schema,
                output_schema=output_schema,
                ui_hints=hints or None,
                examples=examples,
            )
        )

    # Agents, Workflows, Chains by name
    agents = [n for n, _ in global_agent_registry.available_agents()]
    workflows = [n for _, n in registry.list_nodes(NodeType.WORKFLOW)]
    chains = [n for n, _ in global_chain_registry.available_chains()]

    return NodeCatalog(tools=tools, agents=agents, workflows=workflows, chains=chains)


class ModelInfo(BaseModel):
    """Approved model definition exposed to the frontend.

    Parameters
    ----------
    id : str
        Provider-specific model identifier (e.g., "gpt-4o").
    provider : str
        Provider key (e.g., "openai", "anthropic").
    label : str
        Human-friendly name for UI display.
    tags : list[str] | None
        Capability tags (e.g., ["vision", "128k"]).
    context_window : int | None
        Max context tokens, when known.
    vision : bool | None
        Whether the model supports image inputs.
    reasoning : bool | None
        Whether the model supports reasoning features.

    Examples
    --------
    >>> ModelInfo(id="gpt-4o", provider="openai", label="GPT-4o", tags=["vision"], context_window=128000)
    """

    id: str
    provider: str
    label: str
    tags: List[str] | None = None
    context_window: int | None = None
    vision: bool | None = None
    reasoning: bool | None = None


class ProviderInfo(BaseModel):
    """Approved provider information for UI grouping.

    Examples
    --------
    >>> ProviderInfo(id="openai", label="OpenAI")
    """

    id: str
    label: str


class ModelsCatalog(BaseModel):
    """Catalog of approved LLM providers/models and defaults for UI.

    Parameters
    ----------
    providers : list[ProviderInfo]
        Enabled providers with display labels.
    models : list[ModelInfo]
        Approved models across providers.
    defaults : dict[str, str]
        Suggested defaults, e.g. {"provider": "openai", "model": "gpt-4o"}.

    Examples
    --------
    >>> ModelsCatalog(providers=[ProviderInfo(id="openai", label="OpenAI")], models=[], defaults={"provider":"openai","model":"gpt-4o"})
    """

    providers: List[ProviderInfo] = Field(default_factory=list)
    models: List[ModelInfo] = Field(default_factory=list)
    defaults: Dict[str, str] = Field(default_factory=dict)


@router.get("/models", response_model=ModelsCatalog)
async def list_models() -> ModelsCatalog:  # noqa: D401
    """Return approved providers and models for UI dropdowns.

    Returns
    -------
    ModelsCatalog
        Providers, models, and UI defaults.

    Examples
    --------
    Basic usage:
    >>> # In a browser client
    >>> # fetch('/api/v1/meta/models').then(r => r.json())
    """

    providers = [
        ProviderInfo(id="openai", label="OpenAI"),
        ProviderInfo(id="anthropic", label="Anthropic"),
        ProviderInfo(id="google", label="Google"),
        ProviderInfo(id="deepseek", label="DeepSeek"),
    ]

    models: List[ModelInfo] = [
        ModelInfo(
            id="gpt-4o",
            provider="openai",
            label="GPT-4o",
            tags=["vision", "128k"],
            context_window=128000,
            vision=True,
        ),
        ModelInfo(
            id="gpt-4o-mini",
            provider="openai",
            label="GPT-4o mini",
            tags=["cheap", "fast", "128k"],
            context_window=128000,
        ),
        ModelInfo(
            id="claude-3-5-sonnet",
            provider="anthropic",
            label="Claude 3.5 Sonnet",
            tags=["reasoning", "200k"],
            context_window=200000,
            reasoning=True,
        ),
        ModelInfo(
            id="gemini-1.5-pro",
            provider="google",
            label="Gemini 1.5 Pro",
            tags=["vision", "1M"],
            context_window=1000000,
            vision=True,
        ),
        ModelInfo(
            id="deepseek-chat",
            provider="deepseek",
            label="DeepSeek Chat",
            tags=["cheap"],
            context_window=None,
        ),
    ]

    defaults = {"provider": "openai", "model": "gpt-4o"}
    return ModelsCatalog(providers=providers, models=models, defaults=defaults)
