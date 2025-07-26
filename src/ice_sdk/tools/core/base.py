"""Base classes for core data manipulation tools."""
from typing import Dict, Any, Optional
from ice_sdk.tools.base import ToolBase


class DataTool(ToolBase):
    """Base class for core data manipulation tools.
    
    These tools handle basic I/O and data transformations without
    requiring external services or AI capabilities.
    """
    
    category: str = "core"
    requires_llm: bool = False
    is_deterministic: bool = True  # Same input always produces same output
    
    def get_category_metadata(self) -> Dict[str, Any]:
        """Return metadata specific to data tools."""
        return {
            "category": self.category,
            "requires_llm": self.requires_llm,
            "is_deterministic": self.is_deterministic,
            "cost_per_call": 0.0,  # Core tools are free
            "typical_latency_ms": 10  # Very fast
        } 