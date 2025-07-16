"""
Top-level API for iceOS: ergonomic, discoverable, and full-power.
"""

from ice_core.models.model_registry import get_default_model_id

# --- Core re-exports (escape hatches) ---
from ice_orchestrator.script_chain import ScriptChain
from ice_sdk import ToolService
from ice_sdk.models.node_models import (
    AiNodeConfig,
    NodeConfig,
    NodeExecutionResult,
    ToolNodeConfig,
)

# --- Ergonomic API ---


class Node:
    @staticmethod
    def ai(name: str):
        return AiNodeBuilder(name)

    @staticmethod
    def tool(name: str):
        return ToolNodeBuilder(name)

    @staticmethod
    def condition(name: str):
        return ConditionNodeBuilder(name)

    @staticmethod
    def nested(name: str):
        return NestedChainNodeBuilder(name)


class AiNodeBuilder:
    def __init__(self, name: str):
        self._name = name
        self._prompt = None
        self._model = get_default_model_id()
        self._dependencies = []
        self._llm_config = {"provider": "openai"}

    def prompt(self, prompt: str):
        self._prompt = prompt
        return self

    def model(self, model: str):
        self._model = model
        return self

    def depends_on(self, *deps):
        self._dependencies.extend(deps)
        return self

    def build(self):
        return AiNodeConfig(
            id=self._name,
            type="ai",
            name=self._name,
            model=self._model,
            prompt=self._prompt or "",
            llm_config=self._llm_config,
            dependencies=list(self._dependencies),
        )

    def __call__(self):
        return self.build()


class ToolNodeBuilder:
    def __init__(self, name: str):
        self._name = name
        self._tool_name = name
        self._tool_args = {}
        self._dependencies = []

    def tool_name(self, tool_name: str):
        self._tool_name = tool_name
        return self

    def tool_args(self, **kwargs):
        self._tool_args.update(kwargs)
        return self

    def depends_on(self, *deps):
        self._dependencies.extend(deps)
        return self

    def build(self):
        return ToolNodeConfig(
            id=self._name,
            type="tool",
            name=self._name,
            tool_name=self._tool_name,
            tool_args=self._tool_args,
            dependencies=list(self._dependencies),
        )

    def __call__(self):
        return self.build()


class ConditionNodeBuilder:
    def __init__(self, name: str):
        self._name = name
        self._expression = None
        self._dependencies = []

    def expression(self, expr: str):
        self._expression = expr
        return self

    def depends_on(self, *deps):
        self._dependencies.extend(deps)
        return self

    def build(self):
        # Placeholder: assumes ConditionNodeConfig exists
        from ice_sdk.models.node_models import ConditionNodeConfig

        return ConditionNodeConfig(
            id=self._name,
            type="condition",
            name=self._name,
            expression=self._expression or "",
            dependencies=list(self._dependencies),
        )

    def __call__(self):
        return self.build()


class NestedChainNodeBuilder:
    def __init__(self, name: str):
        self._name = name
        self._chain = None
        self._dependencies = []

    def chain(self, chain):
        self._chain = chain
        return self

    def depends_on(self, *deps):
        self._dependencies.extend(deps)
        return self

    def build(self):
        # Placeholder: assumes NestedChainConfig exists
        from ice_sdk.models.node_models import NestedChainConfig

        return NestedChainConfig(
            id=self._name,
            type="nested_chain",
            name=self._name,
            chain=self._chain,
            dependencies=list(self._dependencies),
        )

    def __call__(self):
        return self.build()


class Chain:
    def __init__(self, name: str):
        self._name = name
        self._nodes = []
        self._parallelism = 1

    def add_node(self, node):
        # Accept builder or config
        if hasattr(node, "build"):
            node = node.build()
        self._nodes.append(node)
        return self

    def set_parallelism(self, n: int):
        self._parallelism = n
        return self

    def build(self):
        return ScriptChain(
            nodes=self._nodes, name=self._name, persist_intermediate_outputs=True
        )

    def __call__(self):
        return self.build()

    @classmethod
    def from_yaml(cls, path: str):
        # Placeholder: parse YAML and build chain
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)
        # TODO: parse nodes and build Chain
        chain = cls(data.get("name", "ChainFromYAML"))
        # ...parse nodes...
        return chain

    def visualize(self):
        # Placeholder: print a simple graph structure
        print(f"Chain: {self._name}")
        for node in self._nodes:
            print(f"  Node: {getattr(node, 'name', node.id)} (type={node.type})")
        # TODO: output Mermaid or Graphviz


# --- Unified runner ---
def run_chain(chain, input=None, async_=False):
    import asyncio

    sc = chain.build() if hasattr(chain, "build") else chain
    if async_:
        return asyncio.run(sc.execute())
    else:
        return asyncio.run(sc.execute())


# --- Registry/discovery utilities ---
def list_tools():
    return ToolService().available_tools()


def list_nodes():
    # For demo: just AI, Tool, Condition, Nested nodes
    return ["ai", "tool", "condition", "nested_chain"]


def help(obj=None):
    if obj is None:
        print(
            "iceOS top-level API: Chain, Node, run_chain, list_tools, list_nodes, help"
        )
        return
    import pydoc

    pydoc.help(obj)


# --- Escape hatches for power users ---
ScriptChain = ScriptChain
AiNodeConfig = AiNodeConfig
ToolNodeConfig = ToolNodeConfig
NodeConfig = NodeConfig
NodeExecutionResult = NodeExecutionResult

# --- Exceptions (to be expanded) ---
# from ice_sdk.core.validation import SchemaValidationError
# from ice_orchestrator.execution.executor import ExecutionError

__all__ = [
    "Chain",
    "Node",
    "run_chain",
    "list_tools",
    "list_nodes",
    "help",
    "ScriptChain",
    "AiNodeConfig",
    "ToolNodeConfig",
    "NodeConfig",
    "NodeExecutionResult",
]
