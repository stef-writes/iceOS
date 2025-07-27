"""Unified registry for all node implementations."""
from __future__ import annotations
from typing import Dict, Type, Any, Optional, List, Tuple, Callable, Awaitable, TypeAlias, TypeVar, Protocol
from pydantic import BaseModel, PrivateAttr
from ice_core.models import NodeType, INode, NodeConfig, NodeExecutionResult
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
    
    _nodes: Dict[str, Type[INode]] = PrivateAttr(default_factory=dict)
    _instances: Dict[str, INode] = PrivateAttr(default_factory=dict)
    _executors: Dict[str, ExecCallable] = PrivateAttr(default_factory=dict)
    _chains: Dict[str, Any] = PrivateAttr(default_factory=dict)
    # NOTE: Units removed - use workflows instead
    _agents: Dict[str, str] = PrivateAttr(default_factory=dict)  # Maps agent names to import paths
    
    def _make_key(self, node_type: NodeType, name: str) -> str:
        """Create registry key from type and name."""
        return f"{node_type.value}:{name}"
    
    def register_class(self, node_type: NodeType, name: str, implementation: Type[INode]) -> None:
        """Register a node class."""
        key = self._make_key(node_type, name)
        if key in self._nodes:
            raise RegistryError(f"Node {key} already registered")
        self._nodes[key] = implementation
    
    def register_instance(self, node_type: NodeType, name: str, instance: INode) -> None:
        """Register a node instance (for singletons like tools)."""
        key = self._make_key(node_type, name)
        if key in self._instances:
            raise RegistryError(f"Instance {key} already registered")
        self._instances[key] = instance
    
    def get_class(self, node_type: NodeType, name: str) -> Type[INode]:
        """Get a registered node class."""
        key = self._make_key(node_type, name)
        if key not in self._nodes:
            raise RegistryError(f"Node class {key} not found")
        return self._nodes[key]
    
    def get_instance(self, node_type: NodeType, name: str) -> INode:
        """Get or create a node instance."""
        key = self._make_key(node_type, name)
        
        # Return existing instance if available
        if key in self._instances:
            return self._instances[key]
        
        # Otherwise create from class
        if key in self._nodes:
            return self._nodes[key]()
        
        raise RegistryError(f"Node {key} not found")
    
    def list_nodes(self, node_type: Optional[NodeType] = None) -> List[Tuple[NodeType, str]]:
        """List all registered nodes, optionally filtered by type."""
        results = []
        
        for key in list(self._nodes.keys()) + list(self._instances.keys()):
            type_str, name = key.split(":", 1)
            node_type_enum = NodeType(type_str)
            
            if node_type is None or node_type == node_type_enum:
                results.append((node_type_enum, name))
        
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