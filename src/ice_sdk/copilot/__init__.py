"""
ICE Copilot – central Socratic assistant.

Exports
• IceCopilot         – the conversational design partner
• FrostyDemoChain    – miniature reference ScriptChain
"""

from __future__ import annotations

from .agent import IceCopilot  # noqa: F401
from .chain import FrostyDemoChain  # noqa: F401
from .tools import (  # noqa: F401
    FormatOptimizerTool,
    PlatformSplitterTool,
    VoiceApplierTool,
)

__all__: list[str] = [
    "IceCopilot",
    "FrostyDemoChain",
    "VoiceApplierTool",
    "FormatOptimizerTool",
    "PlatformSplitterTool",
]
