"""Unified registry for all node implementations."""
from __future__ import annotations
from typing import Dict, Type, Any, Optional, List, Tuple, Callable, Awaitable, TypeAlias, TypeVar, Protocol
from pydantic import BaseModel, PrivateAttr
from ice_core.models import INode, NodeConfig, NodeExecutionResult
from ice_core.models.enums import NodeType
# Define RegistryError locally to avoid circular imports
class RegistryError(Exception):
    """Base exception for registry operations."""
    pass
from ice_core.protocols.workflow import WorkflowLike
import importlib.metadata as metadata

# Type aliases for node executors
ScriptChain: TypeAlias = WorkflowLike
ExecCallable = Callable[[ScriptChain, NodeConfig, Dict[str, Any]], Awaitable[NodeExecutionResult]]
F = TypeVar("F", bound=ExecCallable)

class NodeExecutor(Protocol):
    """Required async call signature for node executors."""
    async def __call__(
        self,
        chain: ScriptChain,
        cfg: NodeConfig,
        ctx: Dict[str, Any],
    ) -> NodeExecutionResult: ...

class Registry(BaseModel):
    """Single registry for all node types, tools, chains, and executors."""
    
    _nodes: Dict[NodeType, Dict[str, Type[INode]]] = PrivateAttr(default_factory=dict)
    _instances: Dict[NodeType, Dict[str, INode]] = PrivateAttr(default_factory=dict)
    _executors: Dict[str, ExecCallable] = PrivateAttr(default_factory=dict)
    _chains: Dict[str, Any] = PrivateAttr(default_factory=dict)
    # NOTE: Units removed - use workflows instead
    _agents: Dict[str, str] = PrivateAttr(default_factory=dict)  # Maps agent names to import paths
    
    def register_class(self, node_type: NodeType, name: str, implementation: Type[INode]) -> None:
        """Register a node class."""
        if node_type not in self._nodes:
            self._nodes[node_type] = {}
        if name in self._nodes[node_type]:
            raise RegistryError(f"Node {node_type.value}:{name} already registered")
        self._nodes[node_type][name] = implementation
    
    def register_instance(self, node_type: NodeType, name: str, instance: INode) -> None:
        """Register a node instance (for singletons like tools)."""
        if node_type not in self._instances:
            self._instances[node_type] = {}
        if name in self._instances[node_type]:
            raise RegistryError(f"Instance {node_type.value}:{name} already registered")
        self._instances[node_type][name] = instance
    
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
                self._instances[node_type] = {}
            self._instances[node_type][name] = instance
            return instance
        
        raise RegistryError(f"Node {node_type.value}:{name} not found")
    
    def list_nodes(self, node_type: Optional[NodeType] = None) -> List[Tuple[NodeType, str]]:
        """List all registered nodes, optionally filtered by type."""
        results = []
        
        # Collect from class registry
        for nt, names_dict in self._nodes.items():
            if node_type is None or node_type == nt:
                for name in names_dict.keys():
                    results.append((nt, name))
        
        # Collect from instance registry 
        for nt, names_dict in self._instances.items():
            if node_type is None or node_type == nt:
                for name in names_dict.keys():
                    results.append((nt, name))
        
        return sorted(set(results))
    
    def load_entry_points(self, group: str = "iceos.nodes") -> int:
        """Load nodes from Python entry points."""
        count = 0
        
        try:
            eps = metadata.entry_points(group=group)
        except TypeError:
            eps = metadata.entry_points().get(group, [])
        
        for ep in eps:
            try:
                # Entry point format: "type:name = module:class"
                type_str, name = ep.name.split(":", 1)
                node_type = NodeType(type_str)
                
                cls = ep.load()
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
        return NodeType.TOOL in self._instances and name in self._instances[NodeType.TOOL]
    
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
    
    def available_agents(self) -> List[Tuple[str, str]]:
        """List all registered agents with their import paths."""
        return [(name, path) for name, path in sorted(self._agents.items())]

# Global registry instance
registry = Registry()

# Node executor decorator
def register_node(node_type: str) -> Callable[[F], F]:
    """Decorator to register a node executor.
    
    Example:
        @register_node("tool")
        async def tool_executor(chain, cfg, ctx):
            ...
    """
    def decorator(func: F) -> F:
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