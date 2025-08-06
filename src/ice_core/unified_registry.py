"""Unified registry for all node implementations."""

from __future__ import annotations

import importlib.metadata as metadata
import logging
import pathlib
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
)

from pydantic import BaseModel, PrivateAttr

from ice_core.exceptions import RegistryError
from ice_core.models import INode, NodeConfig, NodeExecutionResult
from ice_core.models.enums import NodeType
from ice_core.protocols.workflow import WorkflowLike

# Type aliases for node executors
ExecCallable = Callable[
    [WorkflowLike, Any, Dict[str, Any]], Awaitable[NodeExecutionResult]
]
F = TypeVar("F", bound=ExecCallable)


class NodeExecutor(Protocol):
    """Required async call signature for node executors."""

    async def __call__(
        self,
        chain: WorkflowLike,
        cfg: NodeConfig,
        ctx: Dict[str, Any],
    ) -> NodeExecutionResult: ...


class _ComponentStub:
    """Lightweight placeholder for components when --no-dynamic is used."""

    def __init__(self, node_type: str, import_path: str):
        self.node_type = node_type
        self.import_path = import_path


class Registry(BaseModel):
    """Single registry for all node types, tools, chains, and executors."""

    _nodes: Dict[NodeType, Dict[str, Type[INode]]] = PrivateAttr(default_factory=dict)
    _instances: Dict[NodeType, Dict[str, INode]] = PrivateAttr(default_factory=dict)
    _executors: Dict[str, ExecCallable] = PrivateAttr(default_factory=dict)
    _chains: Dict[str, Any] = PrivateAttr(default_factory=dict)
    # NOTE: Units removed - use workflows instead
    _agents: Dict[str, str] = PrivateAttr(
        default_factory=dict
    )  # Maps agent names to import paths

    def register_class(
        self, node_type: NodeType, name: str, implementation: Type[INode]
    ) -> None:
        """Register a node class."""
        if node_type not in self._nodes:
            self._nodes[node_type] = {}
        if name in self._nodes[node_type]:
            raise RegistryError(f"Node {node_type.value}:{name} already registered")
        self._nodes[node_type][name] = implementation

    def register_instance(
        self, node_type: NodeType, name: str, instance: INode, validate: bool = True
    ) -> None:
        """Register a node instance (for singletons like tools).

        Args:
            node_type: Type of node (TOOL, AGENT, etc.)
            name: Unique name for the instance
            instance: The instance to register
            validate: Whether to validate before registration (default: True)
                     Set to False for testing or internal use
        """
        # Validate before registration if requested
        if validate and node_type == NodeType.TOOL:
            # Basic validation - check if instance has required methods
            from ice_core.base_tool import ToolBase
            from ice_core.utils.registry_utils import validate_registry_entry

            # Ensure the instance is a ToolBase subclass
            if not isinstance(instance, ToolBase):
                raise RegistryError(
                    f"Tool '{name}' must subclass ice_core.base_tool.ToolBase"
                )
            if not hasattr(instance, "_execute_impl"):
                raise RegistryError(
                    f"Tool '{name}' must implement _execute_impl method"
                )

            # Run comprehensive validation
            try:
                validate_registry_entry(type(instance))
            except Exception as e:
                raise RegistryError(f"Tool '{name}' failed validation: {e}")
            # Check for required attributes
            if not hasattr(instance, "name"):
                raise RegistryError(f"Tool '{name}' must have a 'name' attribute")

            # For now, do synchronous validation
            # Full async validation happens through MCP endpoints
            # This is a compromise to avoid breaking existing sync code

        # Original registration logic
        if node_type not in self._instances:
            self._instances[node_type] = {}  # type: ignore[assignment]
        if name in self._instances[node_type]:
            raise RegistryError(f"Instance {node_type.value}:{name} already registered")
        self._instances[node_type][name] = instance  # type: ignore[assignment]

    def get_class(self, node_type: NodeType, name: str) -> Type[INode]:
        """Get a registered node class."""
        if node_type not in self._nodes or name not in self._nodes[node_type]:
            raise RegistryError(f"Node class {node_type.value}:{name} not found")
        return self._nodes[node_type][name]

    def get_instance(self, node_type: NodeType, name: str) -> INode:
        """Get or create a node instance."""
        # Return existing instance if available
        if node_type in self._instances and name in self._instances[node_type]:
            return self._instances[node_type][name]

        # Otherwise create from class
        if node_type in self._nodes and name in self._nodes[node_type]:
            instance = self._nodes[node_type][name]()
            # Cache the new instance
            if node_type not in self._instances:
                self._instances[node_type] = {}  # type: ignore[assignment]
            self._instances[node_type][name] = instance  # type: ignore[assignment]
            return instance

        raise RegistryError(f"Node {node_type.value}:{name} not found")

    def list_nodes(
        self, node_type: Optional[NodeType] = None
    ) -> List[Tuple[NodeType, str]]:
        """List all registered nodes, optionally filtered by type."""
        results = []

        # Collect from class registry
        for nt, names_dict in self._nodes.items():
            if node_type is None or node_type == nt:
                for name in names_dict.keys():
                    results.append((nt, name))

        # Collect from instance registry
        for nt, names_dict in self._instances.items():  # type: ignore[assignment]
            if node_type is None or node_type == nt:
                for name in names_dict.keys():
                    results.append((nt, name))  # type: ignore[assignment]

        return sorted(set(results))

    def load_entry_points(self, group: str = "iceos.nodes") -> int:
        """Load nodes from Python entry points."""
        count = 0

        try:
            eps = metadata.entry_points(group=group)
        except TypeError:
            eps = metadata.entry_points().get(group, [])  # type: ignore[arg-type]

        for ep in eps:
            try:
                # Entry point format: "type:name = module:class"
                type_str, name = ep.name.split(":", 1)
                node_type = NodeType(type_str)

                cls: Type[INode] = ep.load()  # type: ignore[assignment]
                self.register_class(node_type, name, cls)
                count += 1
            except Exception as e:
                print(f"Failed to load entry point {ep.name}: {e}")

        return count

    # Node executor methods
    def register_executor(self, node_type: str, executor: ExecCallable) -> None:
        """Register a node executor function."""
        if node_type in self._executors:
            raise RegistryError(f"Executor for {node_type} already registered")
        self._executors[node_type] = executor

    def get_executor(self, node_type: str) -> ExecCallable:
        """Get executor for a node type."""
        if node_type not in self._executors:
            raise KeyError(f"No executor registered for node type: {node_type}")
        return self._executors[node_type]

    # Convenience methods for better API
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        if NodeType.TOOL in self._instances:
            return list(self._instances[NodeType.TOOL].keys())
        return []

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    def get_tool(self, name: str) -> INode:
        """Get a tool instance by name."""
        return self.get_instance(NodeType.TOOL, name)

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return (
            NodeType.TOOL in self._instances and name in self._instances[NodeType.TOOL]
        )

    # Chain registry methods
    def register_chain(self, name: str, chain: Any) -> None:
        """Register a reusable chain/workflow."""
        if name in self._chains:
            raise RegistryError(f"Chain {name} already registered")
        self._chains[name] = chain

    def get_chain(self, name: str) -> Any:
        """Get a registered chain."""
        if name not in self._chains:
            raise KeyError(f"Chain {name} not found")
        return self._chains[name]

    def list_chains(self) -> List[str]:
        """List all registered chain names."""
        return sorted(self._chains.keys())

    def available_chains(self) -> List[Tuple[str, Any]]:
        """List all registered chains with their instances."""
        return [(name, chain) for name, chain in sorted(self._chains.items())]

    # ------------------------------------------------------------------
    # Manifest loader (plugins.v0) --------------------------------------
    # ------------------------------------------------------------------

    def load_plugins(
        self, manifest_path: str | "pathlib.Path", allow_dynamic: bool = True
    ) -> int:  # noqa: D401
        """Load components from a *plugins.v0* manifest.

        Args
        ----
        manifest_path:
            Path to a JSON or YAML manifest file.
        allow_dynamic:
            If *False* (`--no-dynamic` flag) the loader registers *metadata only*:
            tools and workflows are not imported, agents are registered with their
            import path.  If *True* (default) the loader attempts to import the
            component immediately and registers the concrete implementation.

        Returns
        -------
        int
            Number of components registered (metadata-only counts when
            *allow_dynamic* is *False*).
        """

        import importlib
        import importlib.util
        import json
        import pathlib

        logger = logging.getLogger(__name__)

        from ice_core.models.plugins import PluginsManifest

        path = pathlib.Path(manifest_path)
        if not path.exists():
            raise RegistryError(f"Manifest not found: {path}")

        raw = path.read_text()
        if path.suffix.lower() in {".yaml", ".yml"}:
            import yaml  # lazy import

            data = yaml.safe_load(raw)
        else:
            data = json.loads(raw)

        manifest = PluginsManifest(**data)

        count = 0
        for comp in manifest.components:
            node_type = comp.node_type
            name = comp.name
            imp_path = comp.import_path

            if node_type == "tool":
                if allow_dynamic:
                    try:
                        module_str, attr = imp_path.split(":", 1)
                        module = importlib.import_module(module_str)
                        obj = getattr(module, attr)
                        # Register class or instance accordingly
                        from ice_core.base_tool import ToolBase

                        if isinstance(obj, type):
                            if not issubclass(obj, ToolBase):
                                raise RegistryError(
                                    f"Tool class {imp_path} is not a subclass of ToolBase"
                                )
                            self.register_class(NodeType.TOOL, name, obj)  # type: ignore[arg-type]
                        else:
                            if not isinstance(obj, ToolBase):
                                raise RegistryError(
                                    f"Tool instance {imp_path} does not inherit ToolBase"
                                )
                            self.register_instance(NodeType.TOOL, name, obj, validate=False)  # type: ignore[arg-type]
                    except Exception as exc:
                        raise RegistryError(
                            f"Failed to import tool {name}: {exc}"
                        ) from exc
                else:
                    # Metadata placeholder – no dynamic import
                    stub = _ComponentStub("tool", imp_path)
                    self._instances.setdefault(NodeType.TOOL, {})[name] = stub  # type: ignore[assignment]

            elif node_type == "agent":
                # Agent registry only stores import path; import happens later
                self.register_agent(name, imp_path)

            elif node_type == "workflow":
                if allow_dynamic:
                    try:
                        module_str, attr = imp_path.split(":", 1)
                        module = importlib.import_module(module_str)
                        chain = getattr(module, attr)
                        self.register_chain(name, chain)
                    except Exception as exc:
                        raise RegistryError(
                            f"Failed to import workflow {name}: {exc}"
                        ) from exc
                else:
                    self._chains[name] = _ComponentStub("workflow", imp_path)  # type: ignore[assignment]

            else:
                raise RegistryError(f"Unknown node_type in manifest: {node_type}")

            logger.debug(
                "pluginRegistered",
                extra={"name": name, "type": node_type, "dynamic": allow_dynamic},
            )
            count += 1

        if manifest.signature is not None:
            logger.warning(
                "pluginsManifest.signature present – verification not implemented yet"
            )

        return count

    # NOTE: Unit methods removed - use workflow registration instead

    # Agent registry methods
    def register_agent(self, name: str, import_path: str) -> None:
        """Register an agent with its import path."""
        if name in self._agents:
            # Skip if already registered with same path (idempotent)
            if self._agents[name] == import_path:
                return
            raise RegistryError(f"Agent {name} already registered with different path")
        self._agents[name] = import_path

    def get_agent_import_path(self, name: str) -> str:
        """Get the import path for a registered agent."""
        if name not in self._agents:
            raise KeyError(f"Agent {name} not found")
        return self._agents[name]

    # ------------------------------------------------------------------
    # New symmetry helpers ---------------------------------------------
    # ------------------------------------------------------------------
    def get_agent_class(self, name: str) -> type:  # noqa: D401
        """Return the imported *class* for the given agent name.

        This performs a lazy import based on the stored import path and
        caches the resulting class object in ``_instances`` for faster
        subsequent access.
        """
        if name not in self._agents:
            raise KeyError(f"Agent {name} not found")

        # Check cached instance/class first
        from typing import cast

        cached: Any = self._instances.get(NodeType.AGENT, {}).get(name)  # type: ignore[arg-type]
        if cached and isinstance(cached, type):
            from typing import cast

            return cast(type, cached)

        import_path = self._agents[name]
        module_str, attr = import_path.split(":", 1)
        import importlib

        module = importlib.import_module(module_str)
        cls = getattr(module, attr)
        if not isinstance(cls, type):
            raise TypeError(f"{import_path} does not resolve to a class")

        # Cache for future look-ups under _instances to avoid re-import
        self._instances.setdefault(NodeType.AGENT, {})[name] = cls  # type: ignore[arg-type,assignment]
        return cls

    def available_agents(self) -> List[Tuple[str, str]]:
        """List all registered agents with their import paths."""
        return [(name, path) for name, path in sorted(self._agents.items())]


# Global registry instance
registry = Registry()

# Node executor decorator
from ice_core.protocols import validated_protocol


def register_node(node_type: str) -> Callable[[F], F]:
    """Decorator to register a node executor.

    Example::

        @register_node("tool")
        async def tool_executor(workflow, cfg, ctx):
            ...
    """

    def decorator(func: F) -> F:
        # Validate protocol compliance (executor signature & coroutine semantics)
        validated_protocol("executor")(func)  # type: ignore[arg-type]
        registry.register_executor(node_type, func)
        return func

    return decorator


# Convenience functions
def get_executor(node_type: str) -> ExecCallable:
    """Get executor for a node type."""
    return registry.get_executor(node_type)


# Direct access to the registry - no backward compatibility needed
global_agent_registry = registry
global_chain_registry = registry
# global_unit_registry removed - use registry directly

# Export commonly used symbols
__all__ = [
    "Registry",
    "registry",
    "register_node",
    "get_executor",
    "NodeExecutor",
    "global_agent_registry",
    "global_chain_registry",
]
