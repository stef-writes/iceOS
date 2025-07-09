"""
ICE Copilot – central Socratic assistant.

Exports
• IceCopilot         – the conversational design partner
• FrostyDemoChain    – miniature reference ScriptChain (demo mode only)
"""

from __future__ import annotations

from .agent import IceCopilot  # noqa: F401
from .tools import (  # noqa: F401
    FormatOptimizerTool,
    PlatformSplitterTool,
    VoiceApplierTool,
)

__all__: list[str] = [
    "IceCopilot",
    "VoiceApplierTool",
    "FormatOptimizerTool",
    "PlatformSplitterTool",
]

# Demo-only exports
from ice_sdk.config import runtime_config

if runtime_config.runtime_mode == "demo":
    from .chain import FrostyDemoChain  # noqa: F401

    __all__.append("FrostyDemoChain")
