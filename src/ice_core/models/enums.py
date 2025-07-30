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

    TOOL = "tool"  # deterministic tool implementation
    LLM = "llm"  # single-prompt LLM operator (no tools)
    CONDITION = "condition"  # if/else branching
    AGENT = "agent"  # LLM + tools + memory
    WORKFLOW = "workflow"  # embed sub-workflows (merged unit/nested_chain)
    LOOP = "loop"  # iteration over collections
    PARALLEL = "parallel"  # concurrent execution branches
    RECURSIVE = "recursive"  # cyclic agent conversations until convergence
    CODE = "code"  # direct code execution
    HUMAN = "human"  # human-in-the-loop approval/input
    MONITOR = "monitor"  # monitoring node for metrics
    SWARM = "swarm"  # multi-agent coordination
