"""Node implementations used by the workflow engine.

| Class | Purpose |
| ----- | ------- |
| `AiNode` | Interacts with LLM providers to generate text or tool calls. |
| `ToolNode` | Wraps a `BaseTool` so it can run inside a Chain as a Node. |
| *(factory)* | `factory.create_node()` helper builds node instances from config. |

All Nodes inherit from `ice_sdk.BaseNode` and must remain *side-effect free*;
any external I/O belongs in Tools. See `.cursorrules` for architecture rules.
"""

from app.nodes.ai.ai_node import AiNode
from ice_sdk.base_node import BaseNode

__all__ = ["BaseNode", "AiNode"]
