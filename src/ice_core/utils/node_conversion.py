from __future__ import annotations

"""Utility helpers for converting design-time MCP *NodeSpec* objects into
runtime *NodeConfig* objects.

Keeping this logic inside *ice_core* prevents higher-level layers from
hard-coding type switches and ensures that the mapping stays in one place.
"""

from typing import Any, Callable, Dict, List, Type, cast

from ice_core.models import (
    AgentNodeConfig,
    CodeNodeConfig,
    ConditionNodeConfig,
    HumanNodeConfig,
    LLMNodeConfig,
    LoopNodeConfig,
    MonitorNodeConfig,
    NodeConfig,
    ParallelNodeConfig,
    RecursiveNodeConfig,
    SwarmNodeConfig,
    ToolNodeConfig,
    WorkflowNodeConfig,
)

__all__: list[str] = [
    "convert_node_spec",
    "convert_node_specs",
]

# ---------------------------------------------------------------------------
# Internal registry ---------------------------------------------------------
# ---------------------------------------------------------------------------

_NODE_TYPE_MAP: Dict[str, Type[NodeConfig]] = {
    # Execution nodes
    "tool": ToolNodeConfig,
    "llm": LLMNodeConfig,
    "agent": AgentNodeConfig,
    "code": CodeNodeConfig,
    # Control flow nodes
    "condition": ConditionNodeConfig,
    "loop": LoopNodeConfig,
    "parallel": ParallelNodeConfig,
    "recursive": RecursiveNodeConfig,
    # Composition node
    "workflow": WorkflowNodeConfig,
    "human": HumanNodeConfig,  # type: ignore[dict-item]
    "monitor": MonitorNodeConfig,  # type: ignore[dict-item]
    "swarm": SwarmNodeConfig,  # type: ignore[dict-item]
}

# ---------------------------------------------------------------------------
# Public API -----------------------------------------------------------------
# ---------------------------------------------------------------------------


def convert_node_spec(spec: Any) -> NodeConfig:
    """Convert a single *NodeSpec* into its concrete :class:`NodeConfig`.

    The incoming object should have at minimum an ``id`` and ``type`` field.
    Subtype fields (``tool_args``, ``prompt``, etc.) are passed through during
    model validation.

    Parameters
    ----------
    spec : NodeSpec
        A MCP node specification object.

    Returns
    -------
    NodeConfig
        A fully validated runtime configuration object.

    Raises
    ------
    ValueError
        If the *type* field is missing or unknown.
    """
    # Import here to avoid circular dependency
    from ice_core.models.mcp import NodeSpec

    # Ensure we have a NodeSpec
    if not isinstance(spec, NodeSpec):
        raise ValueError("Expected NodeSpec instance")

    payload = spec.model_dump()
    node_type = payload.get("type")
    if not node_type:
        from ice_core.exceptions import ValidationError

        raise ValidationError("NodeSpec.type is required for conversion")

    # Alias handling removed – v1.1 now rejects *any* non-canonical node type.

    cfg_cls = _NODE_TYPE_MAP.get(node_type)
    if cfg_cls is None:
        from ice_core.exceptions import UnknownNodeTypeError

        raise UnknownNodeTypeError(str(node_type))

    try:
        return cfg_cls.model_validate(payload)
    except Exception as e:
        from ice_core.exceptions import ValidationError

        raise ValidationError(str(e))


def convert_node_specs(specs: List[Any]) -> List[NodeConfig]:
    """Bulk convert a list of NodeSpec objects."""

    configs = [convert_node_spec(s) for s in specs]

    # Auto-populate schemas for tool nodes
    from ice_core.models.node_models import ToolNodeConfig

    enhanced_configs = []
    for config in configs:
        if isinstance(config, ToolNodeConfig):
            # Apply schema auto-population
            config = populate_tool_node_schemas(config)
        enhanced_configs.append(config)

    return enhanced_configs


def discover_tool_schemas(tool_name: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Discover input and output schemas from a registered tool.

    This bridges the gap between tool definitions and blueprint validation
    by automatically extracting schemas from tool class definitions.

    Args:
        tool_name: Name of the registered tool

    Returns:
        Tuple of (input_schema, output_schema)

    Raises:
        ValueError: If tool is not found in registry
    """
    from ice_core.unified_registry import registry

    try:
        tool = registry.get_tool_instance(tool_name)
    except Exception as e:
        # JIT fallback: attempt to rehydrate from the repo if available.
        try:
            import types as _types

            from ice_api.services.component_repo import choose_component_repo
            from ice_api.services.component_service import ComponentService
            from ice_core.models.mcp import ComponentDefinition as _CDef
            from ice_core.unified_registry import (
                register_tool_factory_callable as _reg_callable,
            )

            # Minimal app stub for repo chooser when outside FastAPI context
            _stub_app = _types.SimpleNamespace(
                app=_types.SimpleNamespace(state=_types.SimpleNamespace())
            )
            repo = choose_component_repo(_stub_app)
            svc = ComponentService(repo)
            rec: Any | None = None
            _lock: Any | None = None
            try:
                rec, _lock = (
                    __import__("asyncio")
                    .get_event_loop()
                    .run_until_complete(svc.get("tool", tool_name))
                )
            except Exception:
                rec, _lock = None, None
            if isinstance(rec, dict):
                definition = rec.get("definition")
                if isinstance(definition, dict):
                    d = _CDef(**definition)
                    # Materialize a callable factory from class code if present
                    tool_class_code = d.tool_class_code
                    factory_code = d.tool_factory_code
                    if tool_class_code:
                        ns: dict[str, Any] = {}
                        exec(tool_class_code, ns)
                        # pick the first subclass of ToolBase
                        from ice_core.base_tool import ToolBase

                        klass: Type[ToolBase] | None = None
                        for name, obj in ns.items():
                            try:
                                if (
                                    isinstance(obj, type)
                                    and issubclass(obj, ToolBase)
                                    and obj is not ToolBase
                                ):
                                    klass = obj
                                    break
                            except Exception:
                                continue
                        if klass is None:
                            raise KeyError(
                                "No ToolBase subclass found in tool_class_code"
                            )

                        # Narrow Optional away for mypy
                        assert klass is not None
                        tool_cls: Type[ToolBase] = klass

                        from ice_core.protocols.node import INode

                        def _factory(**kwargs: Any) -> INode:  # type: ignore[override]
                            return cast(INode, tool_cls(**kwargs))

                        _reg_callable(d.name, _factory)
                    elif factory_code:
                        # Fall back: exec factory code and find a callable returning ToolBase
                        ns2: dict[str, Any] = {}
                        exec(factory_code, ns2)
                        from ice_core.base_tool import ToolBase

                        fac = None
                        for name, obj in ns2.items():
                            if callable(obj):
                                try:
                                    inst = obj()
                                    if isinstance(inst, ToolBase):
                                        fac = obj
                                        break
                                except Exception:
                                    continue
                        if fac is None:
                            raise KeyError("No valid factory in tool_factory_code")
                        from ice_core.protocols.node import INode

                        _reg_callable(d.name, cast("Callable[..., INode]", fac))
                    # Retry fetch after JIT registration
                    tool = registry.get_tool_instance(tool_name)
                else:
                    raise KeyError
            else:
                raise KeyError
        except Exception:
            from ice_core.exceptions import ToolFactoryResolutionError

            raise ToolFactoryResolutionError(tool_name, f"not found in registry: {e}")

    # Get schemas from tool class methods
    input_schema = {}
    output_schema = {}

    if hasattr(tool, "get_input_schema"):
        try:
            input_schema = tool.get_input_schema()
        except Exception:
            # Fallback to basic schema
            input_schema = {"type": "object", "properties": {}}

    if hasattr(tool, "get_output_schema"):
        try:
            output_schema = tool.get_output_schema()
        except Exception:
            # Fallback to basic schema
            output_schema = {"type": "object", "properties": {"result": {}}}

    # If schemas are still empty, provide sensible defaults
    if not input_schema or input_schema == {}:
        input_schema = {"type": "object", "properties": {}}
    if not output_schema or output_schema == {}:
        output_schema = {"type": "object", "properties": {"result": {}}}

    return input_schema, output_schema


def populate_tool_node_schemas(config: "ToolNodeConfig") -> "ToolNodeConfig":
    """Auto-populate schemas for ToolNodeConfig from registered tool.

    This is the blueprint layer's automatic schema discovery - it takes a
    ToolNodeConfig with potentially empty schemas and populates them from
    the actual tool implementation.

    Args:
        config: ToolNodeConfig that may have empty schemas

    Returns:
        Updated ToolNodeConfig with populated schemas
    """
    # Check if schemas are already populated (non-empty dicts)
    has_input_schema = (
        config.input_schema
        and isinstance(config.input_schema, dict)
        and len(config.input_schema) > 0
    )
    has_output_schema = (
        config.output_schema
        and isinstance(config.output_schema, dict)
        and len(config.output_schema) > 0
    )

    # If both schemas are already populated, return as-is
    # Consider fallback placeholder schema {"result": {}} as missing
    def _is_placeholder(sch: Any) -> bool:
        return isinstance(sch, dict) and sch.get("properties") == {"result": {}}

    if (
        has_input_schema
        and has_output_schema
        and not _is_placeholder(config.output_schema)
    ):
        return config

    # Discover schemas from the registered tool
    try:
        input_schema, output_schema = discover_tool_schemas(config.tool_name)

        # Only update empty schemas
        if not has_input_schema:
            config.input_schema = input_schema
        if (not has_output_schema) or _is_placeholder(config.output_schema):
            config.output_schema = output_schema

    except ValueError as e:
        # If tool discovery fails, provide minimal schemas for validation
        import warnings

        warnings.warn(f"Could not discover schemas for tool '{config.tool_name}': {e}")

        if not has_input_schema:
            config.input_schema = {"type": "object", "properties": {}}
        if not has_output_schema:
            config.output_schema = {"type": "object", "properties": {"result": {}}}

    return config
