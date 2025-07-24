"""Enumerations shared by core domain models."""

from __future__ import annotations

from enum import Enum

__all__: list[str] = [
    "ModelProvider",
]

class ModelProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"

# ---------------------------------------------------------------------------
# NodeType enum (canonical runtime discriminator values) ---------------------
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    """Canonical discriminator strings for *NodeConfig.type* field.

    Only *canonical* names are exposed; all aliases have been removed.
    """

    TOOL = "tool"  # deterministic tool implementation (formerly "tool")
    LLM = "llm"  # single-prompt LLM operator
    CONDITION = "condition"
    NESTED_CHAIN = "nested_chain"
    AGENT = "agent"  # pre-built iterative agent
    UNIT = "unit"  # stateless composition of nodes
    WORKFLOW = "workflow"  # reusable sub-workflows
    LOOP = "loop"  # iteration over collections
    PARALLEL = "parallel"  # concurrent execution branches
    CODE = "code"  # direct code execution
