from typing import Any, Callable, Dict, TypeVar

from ice_sdk.interfaces.chain import ScriptChainLike as ScriptChain
from ice_sdk.models.node_models import NodeConfig, NodeExecutionResult

ExecCallable = Callable[[ScriptChain, NodeConfig, Dict[str, Any]], NodeExecutionResult]
F = TypeVar("F", bound=ExecCallable)

NODE_REGISTRY: Dict[str, ExecCallable]

def register_node(mode: str) -> Callable[[F], F]: ...
def get_executor(mode: str) -> ExecCallable: ...
