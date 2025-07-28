"""Real-time workflow monitoring module.

This module contains monitoring functionality including:
- Real-time metric evaluation with expressions
- Alert system integration with multiple channels
- Workflow control actions (pause, abort, alert-only)
- NetworkX graph intelligence integration for smart monitoring
"""

from .base import MonitorNode
from .metrics import MetricsEvaluator, MonitoringResult
from .alerting import AlertManager

# MonitorNodeConfig is imported from ice_core.models.node_models
from ice_core.models.node_models import MonitorNodeConfig

__all__ = [
    "MonitorNode",
    "MonitorNodeConfig",  # Re-exported from ice_core for convenience
    "MetricsEvaluator",
    "MonitoringResult",
    "AlertManager",
] 