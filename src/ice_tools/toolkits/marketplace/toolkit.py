"""Marketplace toolkit – bundles all marketplace conversation tools and agents.

This toolkit provides agents and tools for handling Facebook Marketplace inquiries,
conversation memory, human triggers, and listing status management.
"""

from __future__ import annotations

from typing import List

from ice_core.base_tool import ToolBase
from ice_core.toolkits.base import BaseToolkit

# Import tools and agents
from .human_trigger_tool import HumanTriggerTool
from .listing_status_updater_tool import ListingStatusUpdaterTool

__all__: list[str] = ["MarketplaceToolkit"]


class MarketplaceToolkit(BaseToolkit):
    """Bundle all marketplace conversation tools and agents."""

    # ------------------------------------------------------------------
    # Mandatory BaseToolkit attributes
    # ------------------------------------------------------------------

    name: str = "marketplace"

    # ------------------------------------------------------------------
    # Toolkit API implementation
    # ------------------------------------------------------------------

    @classmethod
    def dependencies(cls) -> List[str]:
        """Return optional runtime dependencies."""
        return []

    def get_tools(self, *, include_extras: bool = False) -> List[ToolBase]:
        """Instantiate all marketplace tools."""

        human_trigger = HumanTriggerTool()
        listing_updater = ListingStatusUpdaterTool()

        return [
            human_trigger,
            listing_updater,
        ]

    def get_agents(self) -> List[str]:
        """Return list of agent names in this toolkit."""
        return ["marketplace_conversation_agent", "listing_status_agent"]
