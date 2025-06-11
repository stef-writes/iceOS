"""Agent orchestrators for Chains and Nodes.

| Class | Purpose |
| ----- | ------- |
| `RouterAgent` | High-level agent that dispatches user requests to the correct workflow. |
| `WorkflowAgentAdapter` | Adapter turning a declarative workflow config into executable agent steps. |
| `NodeAgentAdapter` | Wraps a single `BaseNode` so it can be invoked via the agent interface. |
| `AgentTool` | Exposes agent orchestration as a Tool (for self-hosting within chains). |
| `AgentRegistry` | Runtime lookup & registration of agents. |

All agents are **async** and should avoid blocking the event loop.
"""

__all__ = [
    "NodeAgentAdapter",
    "AgentRegistry",
    "RouterAgent",
    "WorkflowAgentAdapter",
    "AgentTool",
]
from .agent_tool import AgentTool
from .node_agent_adapter import NodeAgentAdapter
from .registry import AgentRegistry
from .router_agent import RouterAgent
from .workflow_agent_adapter import WorkflowAgentAdapter
