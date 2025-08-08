"""Core tool collection.

Currently exposes `AgentTool` to allow Agent-as-Tool composition at the core layer.
"""

from __future__ import annotations

from .agent_tool import AgentTool

__all__ = ["AgentTool"]
