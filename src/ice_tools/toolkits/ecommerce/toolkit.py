"""E-commerce toolkit – bundles all listing-workflow tools with one config.

Why a toolkit?
--------------
A *toolkit* is a thin factory that produces fully-initialised :class:`ice_core.base_tool.ToolBase`
instances.  Grouping related tools under one validated configuration avoids
repeating common parameters (model, margin, test_mode…) in blueprint YAML and
in Python demos.

This concrete implementation lives in **ice_tools** (tool layer):
core contains only the *abstract* `BaseToolkit`.
"""

from __future__ import annotations

from typing import List

from pydantic import Field, PositiveFloat

from ice_core.base_tool import ToolBase
from ice_core.toolkits.base import BaseToolkit

from ..common.csv_loader import CSVLoaderTool

# Import tool classes _lazily_ so static analysers see the names but we avoid
# side-effects on module import (tools register themselves when the class is
# *instantiated*, not at import time).
from .aggregator import AggregatorTool
from .listing_agent import ListingAgentTool
from .marketplace_client import MarketplaceClientTool
from .pricing_strategy import PricingStrategyTool
from .title_description_generator import TitleDescriptionGeneratorTool

__all__: list[str] = ["EcommerceToolkit"]


class EcommerceToolkit(BaseToolkit):
    """Bundle all built-in e-commerce tools under one validated config."""

    # ------------------------------------------------------------------
    # Mandatory BaseToolkit attributes
    # ------------------------------------------------------------------

    name: str = "ecommerce"

    # ------------------------------------------------------------------
    # Shared configuration for the listing workflow
    # ------------------------------------------------------------------

    model: str = Field("gpt-4o", description="LLM model for copy generation")
    margin_percent: PositiveFloat = Field(
        25.0, description="Desired profit margin (0-100)"
    )
    test_mode: bool = Field(
        False, description="Run tools in offline mode (no network I/O)"
    )
    upload: bool = Field(
        True,
        description="Whether to POST listings to marketplace (requires API key)",
    )

    # ------------------------------------------------------------------
    # Toolkit API implementation
    # ------------------------------------------------------------------

    @classmethod
    def dependencies(cls) -> List[str]:
        """Return optional runtime dependencies (none for built-ins)."""

        # In a real third-party toolkit we would list extras (e.g. "pandas>=2.2").
        return []

    # ------------------------------------------------------------------
    # Factory – create fresh tool instances each call
    # ------------------------------------------------------------------

    def get_tools(
        self, *, include_extras: bool = False
    ) -> List[ToolBase]:  # noqa: D401
        """Instantiate every tool in the bundle with shared config applied."""

        # CSV loader is config-free; path/delimiter are runtime inputs.
        csv_loader = CSVLoaderTool(path="/dev/null")

        pricing_tool = PricingStrategyTool(margin_percent=self.margin_percent)

        copy_tool = TitleDescriptionGeneratorTool(
            model=self.model, test_mode=self.test_mode
        )

        marketplace_tool = MarketplaceClientTool(test_mode=self.test_mode)

        listing_tool = ListingAgentTool(
            margin_percent=self.margin_percent,
            model=self.model,
            test_mode=self.test_mode,
            upload=self.upload,
        )

        aggregator_tool = AggregatorTool()

        return [
            csv_loader,
            pricing_tool,
            copy_tool,
            marketplace_tool,
            listing_tool,
            aggregator_tool,
        ]
