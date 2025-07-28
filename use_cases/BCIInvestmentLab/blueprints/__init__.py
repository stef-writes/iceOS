"""BCI Investment Lab - Modular MCP Blueprints

Clean, reusable blueprint modules for investment analysis workflows.
Each blueprint demonstrates different iceOS node types and capabilities.
"""

from .literature_analysis import create_literature_analysis_blueprint
from .market_monitoring import create_market_monitoring_blueprint
from .recursive_synthesis import create_recursive_synthesis_blueprint

__all__ = [
    "create_literature_analysis_blueprint",
    "create_market_monitoring_blueprint", 
    "create_recursive_synthesis_blueprint"
] 