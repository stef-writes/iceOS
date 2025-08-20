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
from ice_core.models.mcp import AgentDefinition
from ice_core.protocols.agent import IAgent
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
    _tool_factories: Dict[str, str] = PrivateAttr(
        default_factory=dict
    )  # Maps tool names to factory import paths
    _tool_factory_cache: Dict[str, Callable[..., INode]] = PrivateAttr(
        default_factory=dict
    )
    # Workflow factory registry (module:function strings)
    _workflow_factories: Dict[str, str] = PrivateAttr(default_factory=dict)
    _workflow_factory_cache: Dict[str, Callable[..., "WorkflowLike"]] = PrivateAttr(
        default_factory=dict
    )
    # LLM factory registry (module:function strings)
    _llm_factories: Dict[str, str] = PrivateAttr(default_factory=dict)
    _llm_factory_cache: Dict[str, Callable[..., Any]] = PrivateAttr(
        default_factory=dict
    )
    # Control/advanced node factory registries
    _condition_factories: Dict[str, str] = PrivateAttr(default_factory=dict)
    _condition_factory_cache: Dict[str, Callable[..., Any]] = PrivateAttr(
        default_factory=dict
    )
    _loop_factories: Dict[str, str] = PrivateAttr(default_factory=dict)
    _loop_factory_cache: Dict[str, Callable[..., Any]] = PrivateAttr(
        default_factory=dict
    )
    _parallel_factories: Dict[str, str] = PrivateAttr(default_factory=dict)
    _parallel_factory_cache: Dict[str, Callable[..., Any]] = PrivateAttr(
        default_factory=dict
    )
    _recursive_factories: Dict[str, str] = PrivateAttr(default_factory=dict)
    _recursive_factory_cache: Dict[str, Callable[..., Any]] = PrivateAttr(
        default_factory=dict
    )
    _code_factories: Dict[str, str] = PrivateAttr(default_factory=dict)
    _code_factory_cache: Dict[str, Callable[..., Any]] = PrivateAttr(
        default_factory=dict
    )
    _human_factories: Dict[str, str] = PrivateAttr(default_factory=dict)
    _human_factory_cache: Dict[str, Callable[..., Any]] = PrivateAttr(
        default_factory=dict
    )
    _monitor_factories: Dict[str, str] = PrivateAttr(default_factory=dict)
    _monitor_factory_cache: Dict[str, Callable[..., Any]] = PrivateAttr(
        default_factory=dict
    )
    _swarm_factories: Dict[str, str] = PrivateAttr(default_factory=dict)
    _swarm_factory_cache: Dict[str, Callable[..., Any]] = PrivateAttr(
        default_factory=dict
    )

    def register_class(
        self, node_type: NodeType, name: str, implementation: Type[INode]
    ) -> None:
        """Register a node class."""
        if node_type not in self._nodes:
            self._nodes[node_type] = {}
        if name in self._nodes[node_type]:
            raise RegistryError(f"Node {node_type.value}:{name} already registered")
        self._nodes[node_type][name] = implementation

    # Legacy instance registration removed – factories are the only path

    def get_class(self, node_type: NodeType, name: str) -> Type[INode]:
        """Get a registered node class."""
        if node_type not in self._nodes or name not in self._nodes[node_type]:
            raise RegistryError(f"Node class {node_type.value}:{name} not found")
        return self._nodes[node_type][name]

    # Legacy instance retrieval removed – factories are the only path

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
        """List all registered tools (classes and factories).

        Returns a stable-sorted union of tool names registered either via
        class registration or via factory registration.
        """
        names: set[str] = set()
        # Class-registered tools
        try:
            names.update(self._nodes.get(NodeType.TOOL, {}).keys())  # type: ignore[index]
        except Exception:
            pass
        # Factory-registered tools
        try:
            names.update(name for name, _ in self.available_tool_factories())
        except Exception:
            pass
        return sorted(names)

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    def get_tool(self, name: str) -> INode:
        """Get a tool instance by name via factory."""
        return self.get_tool_instance(name)

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered (class or factory)."""
        # Factories
        if name in self._tool_factories or name in self._tool_factory_cache:
            return True
        # Classes
        try:
            return name in self._nodes.get(NodeType.TOOL, {})  # type: ignore[index]
        except Exception:
            return False

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
                            # Idempotent class registration: allow duplicate name if it points
                            # to the exact same class object; raise only on conflicting class.
                            existing = self._nodes.get(NodeType.TOOL, {}).get(name)  # type: ignore[index]
                            if existing is not None:
                                # Treat duplicate name as idempotent, even if the class object is a different
                                # identity (e.g., due to reload). The first registered implementation wins.
                                pass
                            else:
                                # obj is a subclass of ToolBase, which implements INode
                                self.register_class(NodeType.TOOL, name, obj)  # type: ignore[arg-type]
                            # Also expose a callable factory so get_tool_instance works with class-based manifests
                            try:
                                # Bind the current class into the closure to avoid late-binding bugs
                                def _factory_bound(
                                    _klass: Type[ToolBase],
                                ) -> Callable[..., INode]:
                                    def _create(**kw: Any) -> INode:
                                        return _klass(**kw)  # type: ignore[return-value]

                                    return _create

                                self._tool_factory_cache[name] = _factory_bound(obj)  # type: ignore[assignment]
                            except Exception:
                                pass
                        else:
                            # Support instance export by wrapping with an auto-generated factory
                            if not isinstance(obj, ToolBase):
                                raise RegistryError(
                                    f"Tool instance {imp_path} does not inherit ToolBase"
                                )
                            # Create a dynamic factory module for this object
                            import sys
                            import types

                            mod_name = f"_dyn_tools_{name}"
                            mod = types.ModuleType(mod_name)

                            def _factory(**kwargs: Any) -> ToolBase:
                                # Return a new instance of the same class if possible; else return the object itself
                                try:
                                    return obj.__class__(**kwargs)
                                except Exception:
                                    return obj

                            setattr(mod, "create", _factory)
                            sys.modules[mod_name] = mod
                            self.register_tool_factory(name, f"{mod_name}:create")
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

    # Data-first agent definitions -------------------------------------
    def register_agent_definition(self, name: str, definition: AgentDefinition) -> None:
        """Register a data-first agent definition in the registry."""
        if not hasattr(self, "_agent_definitions"):
            self._agent_definitions: Dict[str, AgentDefinition] = {}
        existing = self._agent_definitions.get(name)
        if existing == definition:
            return
        self._agent_definitions[name] = definition

    def get_agent_definition(self, name: str) -> AgentDefinition:
        """Retrieve a data-first agent definition or raise KeyError."""
        if not hasattr(self, "_agent_definitions"):
            self._agent_definitions = {}
        if name not in self._agent_definitions:
            raise KeyError(f"Agent definition {name} not found")
        return self._agent_definitions[name]

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

    def get_agent_instance(self, name: str, **kwargs: Any) -> IAgent:
        """Instantiate an agent via its registered factory and return *fresh* instance.

        The factory must return an object that implements the agent protocol and passes
        validation. No instance caching is done – callers receive a new,
        isolated agent each time.
        """
        if name not in self._agents:
            raise KeyError(f"Agent {name} not found")

        # Get the factory function and call it
        import_path = self._agents[name]
        module_str, attr = import_path.split(":", 1)
        import importlib

        module = importlib.import_module(module_str)
        factory = getattr(module, attr)
        if not callable(factory):
            raise TypeError(f"Factory {import_path} is not callable")

        agent_instance = factory(**kwargs)

        # Validate the instance implements the expected protocol
        from ice_core.protocols.agent import IAgent

        if not isinstance(agent_instance, IAgent):
            raise TypeError(f"Factory for {name} did not return an IAgent instance")

        # Run idempotent validate() if the agent exposes it
        if hasattr(agent_instance, "validate") and callable(agent_instance.validate):
            # Check if validate is a coroutine
            import asyncio

            if asyncio.iscoroutinefunction(agent_instance.validate):
                # Skip async validation for now - would need async context
                pass
            else:
                agent_instance.validate()

        return agent_instance

    # ------------------------------------------------------------------
    # Tool factory helpers ---------------------------------------------
    # ------------------------------------------------------------------
    def register_tool_factory(self, name: str, import_path: str) -> None:
        """Register a tool factory import path (``module:create_func``)."""
        if name in self._tool_factories:
            if self._tool_factories[name] == import_path:
                return  # idempotent
            raise RegistryError(
                f"Tool factory {name} already registered with different path"
            )
        self._tool_factories[name] = import_path
        # Preload cache with a wrapper to create instances lazily
        try:
            module_str, attr = import_path.split(":", 1)
            import importlib

            module = importlib.import_module(module_str)
            factory = getattr(module, attr)
            if callable(factory):
                self._tool_factory_cache[name] = factory  # type: ignore[assignment]
        except Exception:
            # Leave cache empty; instance resolution will import at first use
            pass

    def get_tool_instance(self, name: str, **kwargs: Any) -> INode:
        """Instantiate a tool via its registered factory and return *fresh* instance.

        The factory must return an object that inherits ``ToolBase`` and passes
        validation.  No instance caching is done – callers receive a new,
        isolated tool each time.
        """
        # Resolve factory callable (cached for performance). Allow pure-callable
        # registrations that do not have a string import path.
        if name in self._tool_factory_cache:
            factory = self._tool_factory_cache[name]
        elif name in self._tool_factories:
            module_str, attr = self._tool_factories[name].split(":", 1)
            import importlib

            module = importlib.import_module(module_str)
            factory = getattr(module, attr)
            if not callable(factory):
                from ice_core.exceptions import ToolFactoryResolutionError

                raise ToolFactoryResolutionError(
                    name, "factory attribute is not callable"
                )
            self._tool_factory_cache[name] = factory  # Cache for next call
        else:
            # Fallback: if a Tool class is registered under this name, synthesize
            # a callable factory on the fly to preserve class-first registrations.
            try:
                tool_cls = self._nodes.get(NodeType.TOOL, {}).get(name)  # type: ignore[index]
            except Exception:
                tool_cls = None
            if tool_cls is not None:
                try:
                    from ice_core.base_tool import ToolBase as _ToolBase

                    if isinstance(tool_cls, type) and issubclass(tool_cls, _ToolBase):

                        def _factory_bound(**kw: Any) -> INode:
                            return tool_cls(**kw)  # type: ignore[return-value]

                        # Cache synthesized factory for future calls
                        self._tool_factory_cache[name] = _factory_bound  # type: ignore[assignment]
                        factory = _factory_bound
                    else:
                        raise TypeError("registered tool class is invalid")
                except Exception:
                    from ice_core.exceptions import ToolFactoryResolutionError

                    raise ToolFactoryResolutionError(name, "factory not registered")
            else:
                from ice_core.exceptions import ToolFactoryResolutionError

                raise ToolFactoryResolutionError(name, "factory not registered")

        tool_instance = factory(**kwargs)

        from ice_core.base_tool import ToolBase  # Local to avoid circular import

        if not isinstance(tool_instance, ToolBase):
            from ice_core.exceptions import ToolFactoryResolutionError

            raise ToolFactoryResolutionError(
                name, "factory did not return a ToolBase instance"
            )

        # Run idempotent validate() if the tool exposes it
        if hasattr(tool_instance, "validate") and callable(tool_instance.validate):
            # Skip Pydantic's validate method which requires a value argument
            if not hasattr(tool_instance.validate, "__self__"):
                tool_instance.validate()

        return tool_instance

    def available_tool_factories(self) -> List[Tuple[str, str]]:
        """List registered tool factories with their import paths."""
        # Include callable-registered factories with a placeholder path
        entries: List[Tuple[str, str]] = []
        entries.extend(
            (name, path) for name, path in sorted(self._tool_factories.items())
        )
        for name in sorted(self._tool_factory_cache.keys()):
            if name not in self._tool_factories:
                entries.append((name, "<callable>"))
        return entries

    # ------------------------------------------------------------------
    # Test support helpers (safe to call in test environment) ----------
    # ------------------------------------------------------------------
    def clear_llm_factories(self) -> None:
        """Remove all registered LLM factories and caches.

        Intended for test isolation so multiple tests can register different
        factories under the same model name without leaking state across tests.
        """
        self._llm_factories.clear()
        self._llm_factory_cache.clear()

    def clear_tool_factories(self) -> None:
        """Remove all registered Tool factories and caches.

        Useful for test isolation when different tests register the same tool
        name with different import paths.
        """
        self._tool_factories.clear()
        self._tool_factory_cache.clear()

    def available_agents(self) -> List[Tuple[str, str]]:
        """List all registered agents with their import paths."""
        return [(name, path) for name, path in sorted(self._agents.items())]

    # ------------------------------------------------------------------
    # Workflow factory helpers -----------------------------------------
    # ------------------------------------------------------------------
    def register_workflow_factory(self, name: str, import_path: str) -> None:
        """Register a workflow factory import path (``module:create_func``).

        The factory must return an object implementing ``WorkflowLike`` with an
        async ``execute(context: Dict[str, Any]) -> Any`` method and optional
        idempotent ``validate()``.
        """
        if name in self._workflow_factories:
            if self._workflow_factories[name] == import_path:
                return  # idempotent
            raise RegistryError(
                f"Workflow factory {name} already registered with different path"
            )
        self._workflow_factories[name] = import_path

    def get_workflow_instance(self, name: str, **kwargs: Any) -> "WorkflowLike":
        """Instantiate a workflow via its registered factory and return a fresh instance.

        Raises
        ------
        KeyError
            If no workflow factory is registered under ``name``.
        TypeError
            If the resolved factory is not callable or returns an invalid object.
        """
        if name not in self._workflow_factories:
            raise KeyError(f"Workflow factory not registered: {name}")

        # Resolve and cache the factory callable
        if name in self._workflow_factory_cache:
            factory = self._workflow_factory_cache[name]
        else:
            module_str, attr = self._workflow_factories[name].split(":", 1)
            import importlib

            module = importlib.import_module(module_str)
            factory = getattr(module, attr)
            if not callable(factory):
                raise TypeError(
                    f"Workflow factory attribute is not callable: {self._workflow_factories[name]}"
                )
            self._workflow_factory_cache[name] = factory

        instance = factory(**kwargs)

        # Allow coroutine factories – caller (executor) will await the instance
        try:
            import inspect as _inspect

            if _inspect.isawaitable(instance):
                return instance  # type: ignore[return-value]
        except Exception:
            pass

        # Minimal protocol validation – must expose async execute(ctx)
        if not hasattr(instance, "execute") or not callable(
            getattr(instance, "execute")
        ):
            raise TypeError(
                f"Factory for workflow '{name}' did not return an instance with an execute() method"
            )

        # Run optional idempotent validate()
        if hasattr(instance, "validate") and callable(getattr(instance, "validate")):
            try:
                instance.validate()  # type: ignore[call-arg]
            except Exception as exc:  # pragma: no cover - defensive
                raise TypeError(f"Workflow '{name}' failed validate(): {exc}") from exc

        return instance

    def available_workflow_factories(self) -> List[Tuple[str, str]]:
        """List registered workflow factories with their import paths."""
        return [(name, path) for name, path in sorted(self._workflow_factories.items())]

    # ------------------------------------------------------------------
    # LLM factory helpers ----------------------------------------------
    # ------------------------------------------------------------------
    def register_llm_factory(self, name: str, import_path: str) -> None:
        """Register an LLM node factory (``module:create_func``).

        The factory must return an object exposing a ``generate(llm_config, prompt, context)``
        coroutine returning ``tuple[str, Optional[dict[str, int]], Optional[str]]``
        (text, usage, error). This mirrors ``LLMService.generate`` for interchangeability.
        """
        if name in self._llm_factories:
            if self._llm_factories[name] == import_path:
                return
            raise RegistryError(
                f"LLM factory {name} already registered with different path"
            )
        self._llm_factories[name] = import_path

    def get_llm_instance(self, name: str, **kwargs: Any) -> Any:
        """Instantiate an LLM node helper via its factory and return a fresh instance.

        Raises
        ------
        KeyError
            If no LLM factory is registered under ``name``.
        TypeError
            If the resolved factory is not callable or returns an invalid object.
        """
        if name not in self._llm_factories:
            raise KeyError(f"LLM factory not registered: {name}")

        # Resolve and cache the factory callable
        if name in self._llm_factory_cache:
            factory = self._llm_factory_cache[name]
        else:
            module_str, attr = self._llm_factories[name].split(":", 1)
            import importlib

            module = importlib.import_module(module_str)
            factory = getattr(module, attr)
            if not callable(factory):
                raise TypeError(
                    f"LLM factory attribute is not callable: {self._llm_factories[name]}"
                )
            self._llm_factory_cache[name] = factory

        instance = factory(**kwargs)

        # Validate instance has a generate coroutine compatible with LLMService
        generate_attr = getattr(instance, "generate", None)
        if not callable(generate_attr):
            raise TypeError(
                f"Factory for LLM '{name}' did not return an instance with a generate() method"
            )

        return instance

    # ------------------------------------------------------------------
    # Generic helper to resolve factories from a map+cache --------------
    # ------------------------------------------------------------------
    def _resolve_factory(
        self,
        registry_map: Dict[str, str],
        cache: Dict[str, Callable[..., Any]],
        name: str,
    ) -> Callable[..., Any]:
        if name in cache:
            return cache[name]
        if name not in registry_map:
            raise KeyError(name)
        module_str, attr = registry_map[name].split(":", 1)
        import importlib

        module = importlib.import_module(module_str)
        factory = getattr(module, attr)
        if not callable(factory):
            raise TypeError(f"Factory attribute is not callable: {registry_map[name]}")
        cache[name] = factory
        # Factory is callable but may be untyped; help mypy with a Callable[..., Any] signature
        from typing import cast as _cast

        return _cast(Callable[..., Any], factory)

    # ------------------------------------------------------------------
    # Condition factory helpers ----------------------------------------
    # ------------------------------------------------------------------
    def register_condition_factory(self, name: str, import_path: str) -> None:
        if (
            name in self._condition_factories
            and self._condition_factories[name] != import_path
        ):
            raise RegistryError(
                f"Condition factory {name} already registered with different path"
            )
        self._condition_factories[name] = import_path

    def get_condition_instance(self, name: str, **kwargs: Any) -> Any:
        factory = self._resolve_factory(
            self._condition_factories, self._condition_factory_cache, name
        )
        return factory(**kwargs)

    # ------------------------------------------------------------------
    # Loop factory helpers ---------------------------------------------
    # ------------------------------------------------------------------
    def register_loop_factory(self, name: str, import_path: str) -> None:
        if name in self._loop_factories and self._loop_factories[name] != import_path:
            raise RegistryError(
                f"Loop factory {name} already registered with different path"
            )
        self._loop_factories[name] = import_path

    def get_loop_instance(self, name: str, **kwargs: Any) -> Any:
        factory = self._resolve_factory(
            self._loop_factories, self._loop_factory_cache, name
        )
        return factory(**kwargs)

    # ------------------------------------------------------------------
    # Parallel factory helpers -----------------------------------------
    # ------------------------------------------------------------------
    def register_parallel_factory(self, name: str, import_path: str) -> None:
        if (
            name in self._parallel_factories
            and self._parallel_factories[name] != import_path
        ):
            raise RegistryError(
                f"Parallel factory {name} already registered with different path"
            )
        self._parallel_factories[name] = import_path

    def get_parallel_instance(self, name: str, **kwargs: Any) -> Any:
        factory = self._resolve_factory(
            self._parallel_factories, self._parallel_factory_cache, name
        )
        return factory(**kwargs)

    # ------------------------------------------------------------------
    # Recursive factory helpers ----------------------------------------
    # ------------------------------------------------------------------
    def register_recursive_factory(self, name: str, import_path: str) -> None:
        if (
            name in self._recursive_factories
            and self._recursive_factories[name] != import_path
        ):
            raise RegistryError(
                f"Recursive factory {name} already registered with different path"
            )
        self._recursive_factories[name] = import_path

    def get_recursive_instance(self, name: str, **kwargs: Any) -> Any:
        factory = self._resolve_factory(
            self._recursive_factories, self._recursive_factory_cache, name
        )
        return factory(**kwargs)

    # ------------------------------------------------------------------
    # Code factory helpers ---------------------------------------------
    # ------------------------------------------------------------------
    def register_code_factory(self, name: str, import_path: str) -> None:
        if name in self._code_factories and self._code_factories[name] != import_path:
            raise RegistryError(
                f"Code factory {name} already registered with different path"
            )
        self._code_factories[name] = import_path

    def get_code_instance(self, name: str, **kwargs: Any) -> Any:
        factory = self._resolve_factory(
            self._code_factories, self._code_factory_cache, name
        )
        return factory(**kwargs)

    def has_code_factory(self, name: str) -> bool:
        """Return True if a code factory is registered or cached under name."""
        return name in self._code_factories or name in self._code_factory_cache

    # ------------------------------------------------------------------
    # Human factory helpers --------------------------------------------
    # ------------------------------------------------------------------
    def register_human_factory(self, name: str, import_path: str) -> None:
        if name in self._human_factories and self._human_factories[name] != import_path:
            raise RegistryError(
                f"Human factory {name} already registered with different path"
            )
        self._human_factories[name] = import_path

    def get_human_instance(self, name: str, **kwargs: Any) -> Any:
        factory = self._resolve_factory(
            self._human_factories, self._human_factory_cache, name
        )
        return factory(**kwargs)

    # ------------------------------------------------------------------
    # Monitor factory helpers ------------------------------------------
    # ------------------------------------------------------------------
    def register_monitor_factory(self, name: str, import_path: str) -> None:
        if (
            name in self._monitor_factories
            and self._monitor_factories[name] != import_path
        ):
            raise RegistryError(
                f"Monitor factory {name} already registered with different path"
            )
        self._monitor_factories[name] = import_path

    def get_monitor_instance(self, name: str, **kwargs: Any) -> Any:
        factory = self._resolve_factory(
            self._monitor_factories, self._monitor_factory_cache, name
        )
        return factory(**kwargs)

    # ------------------------------------------------------------------
    # Swarm factory helpers --------------------------------------------
    # ------------------------------------------------------------------
    def register_swarm_factory(self, name: str, import_path: str) -> None:
        if name in self._swarm_factories and self._swarm_factories[name] != import_path:
            raise RegistryError(
                f"Swarm factory {name} already registered with different path"
            )
        self._swarm_factories[name] = import_path

    def get_swarm_instance(self, name: str, **kwargs: Any) -> Any:
        factory = self._resolve_factory(
            self._swarm_factories, self._swarm_factory_cache, name
        )
        return factory(**kwargs)


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


# ------------------------------------------------------------------
# Factory helpers (module-level wrappers) ---------------------------
# ------------------------------------------------------------------


def register_tool_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register a tool factory at module level for callers that don’t need class access."""
    registry.register_tool_factory(name, import_path)


def register_tool_factory_callable(name: str, factory: Callable[..., INode]) -> None:  # noqa: D401
    """Register a tool factory directly via a callable.

    This avoids dynamic module import paths and aligns with repo-driven
    rehydration/JIT where code objects are materialised at runtime.
    """
    # Overwrite cache entry; keep mapping idempotent
    registry._tool_factory_cache[name] = factory  # type: ignore[attr-defined]


def get_tool_instance(name: str, **kwargs: Any) -> INode:  # noqa: D401
    """Convenience wrapper around ``Registry.get_tool_instance``."""
    return registry.get_tool_instance(name, **kwargs)


def register_agent_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register an agent factory at module level for callers that don't need class access."""
    registry.register_agent(name, import_path)


def register_workflow_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register a workflow factory at module level."""
    registry.register_workflow_factory(name, import_path)


def get_workflow_instance(name: str, **kwargs: Any) -> "WorkflowLike":  # noqa: D401
    """Convenience wrapper for ``Registry.get_workflow_instance``."""
    return registry.get_workflow_instance(name, **kwargs)


def register_llm_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register an LLM node factory at module level."""
    registry.register_llm_factory(name, import_path)


def get_llm_instance(name: str, **kwargs: Any) -> Any:  # noqa: D401
    """Convenience wrapper for ``Registry.get_llm_instance``."""
    return registry.get_llm_instance(name, **kwargs)


def clear_llm_factories() -> None:  # noqa: D401
    """Clear LLM factories (test helper)."""
    registry.clear_llm_factories()


def clear_tool_factories() -> None:  # noqa: D401
    """Clear Tool factories (test helper)."""
    registry.clear_tool_factories()


# Condition wrappers ---------------------------------------------------------
def register_condition_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register a condition node factory at module level."""
    registry.register_condition_factory(name, import_path)


def get_condition_instance(name: str, **kwargs: Any) -> Any:  # noqa: D401
    """Convenience wrapper for ``Registry.get_condition_instance``."""
    return registry.get_condition_instance(name, **kwargs)


# Loop wrappers --------------------------------------------------------------
def register_loop_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register a loop node factory at module level."""
    registry.register_loop_factory(name, import_path)


def get_loop_instance(name: str, **kwargs: Any) -> Any:  # noqa: D401
    """Convenience wrapper for ``Registry.get_loop_instance``."""
    return registry.get_loop_instance(name, **kwargs)


# Parallel wrappers ----------------------------------------------------------
def register_parallel_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register a parallel node factory at module level."""
    registry.register_parallel_factory(name, import_path)


def get_parallel_instance(name: str, **kwargs: Any) -> Any:  # noqa: D401
    """Convenience wrapper for ``Registry.get_parallel_instance``."""
    return registry.get_parallel_instance(name, **kwargs)


# Recursive wrappers ---------------------------------------------------------
def register_recursive_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register a recursive node factory at module level."""
    registry.register_recursive_factory(name, import_path)


def get_recursive_instance(name: str, **kwargs: Any) -> Any:  # noqa: D401
    """Convenience wrapper for ``Registry.get_recursive_instance``."""
    return registry.get_recursive_instance(name, **kwargs)


# Code wrappers --------------------------------------------------------------
def register_code_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register a code node factory at module level."""
    registry.register_code_factory(name, import_path)


def has_code_factory(name: str) -> bool:  # noqa: D401
    """Check existence of a code factory by name."""
    return registry.has_code_factory(name)


def get_code_instance(name: str, **kwargs: Any) -> Any:  # noqa: D401
    """Convenience wrapper for ``Registry.get_code_instance``."""
    return registry.get_code_instance(name, **kwargs)


# Human wrappers -------------------------------------------------------------
def register_human_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register a human node factory at module level."""
    registry.register_human_factory(name, import_path)


def get_human_instance(name: str, **kwargs: Any) -> Any:  # noqa: D401
    """Convenience wrapper for ``Registry.get_human_instance``."""
    return registry.get_human_instance(name, **kwargs)


# Monitor wrappers -----------------------------------------------------------
def register_monitor_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register a monitor node factory at module level."""
    registry.register_monitor_factory(name, import_path)


def get_monitor_instance(name: str, **kwargs: Any) -> Any:  # noqa: D401
    """Convenience wrapper for ``Registry.get_monitor_instance``."""
    return registry.get_monitor_instance(name, **kwargs)


# Swarm wrappers -------------------------------------------------------------
def register_swarm_factory(name: str, import_path: str) -> None:  # noqa: D401
    """Register a swarm node factory at module level."""
    registry.register_swarm_factory(name, import_path)


def get_swarm_instance(name: str, **kwargs: Any) -> Any:  # noqa: D401
    """Convenience wrapper for ``Registry.get_swarm_instance``."""
    return registry.get_swarm_instance(name, **kwargs)


# Direct access to the registry - no backward compatibility needed
global_agent_registry = registry
global_chain_registry = registry
# global_unit_registry removed - use registry directly

# Export commonly used symbols
__all__ = [
    "Registry",
    "registry",
    "register_node",
    "register_tool_factory",
    "register_agent_factory",
    "register_workflow_factory",
    "register_llm_factory",
    "register_condition_factory",
    "register_loop_factory",
    "register_parallel_factory",
    "register_recursive_factory",
    "register_code_factory",
    "register_human_factory",
    "register_monitor_factory",
    "register_swarm_factory",
    "get_tool_instance",
    "get_workflow_instance",
    "get_llm_instance",
    "get_condition_instance",
    "get_loop_instance",
    "get_parallel_instance",
    "get_recursive_instance",
    "get_code_instance",
    "get_human_instance",
    "get_monitor_instance",
    "get_swarm_instance",
    "get_executor",
    "NodeExecutor",
    "global_agent_registry",
    "global_chain_registry",
]
