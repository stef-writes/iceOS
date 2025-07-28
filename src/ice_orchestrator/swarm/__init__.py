"""Swarm coordination module for multi-agent orchestration.

This module contains swarm coordination functionality including:
- Multi-agent coordination strategies (consensus, hierarchical, marketplace)
- Shared memory pool management for agent coordination
- Agent execution orchestration and result synthesis
- Convergence detection and round management
"""

from .base import SwarmNode
from .strategies import ConsensusStrategy, HierarchicalStrategy, MarketplaceStrategy
from .coordinator import SwarmCoordinator

# SwarmNodeConfig is imported from ice_core.models.node_models
from ice_core.models.node_models import SwarmNodeConfig

__all__ = [
    "SwarmNode",
    "SwarmNodeConfig",  # Re-exported from ice_core for convenience
    "ConsensusStrategy", 
    "HierarchicalStrategy",
    "MarketplaceStrategy",
    "SwarmCoordinator",
] 