"""
Purpose: Full cognitive system state including memory, confidence, and partial plans
Layer: Support/Models
Dependencies: All cognitive subsystem states, conversation context
"""

# LEVERAGE iceOS:
# - Follow ice_core.models patterns with Pydantic BaseModel
# - Use same validation patterns as NodeConfig models
# - Integrate with ice_core.models.mcp.PartialBlueprint
#
# Core model structure (following iceOS patterns):
# from pydantic import BaseModel, Field
# from typing import Dict, List, Optional, Any
# from ice_core.models.mcp import PartialBlueprint
#
# class CognitiveState(BaseModel):
#     """State of Frosty's cognitive system at a point in time."""
#     
#     # Conversation context
#     session_id: str = Field(..., description="Current session identifier")
#     turn_count: int = Field(0, description="Number of turns in conversation")
#     
#     # Current understanding
#     active_intent: Optional[Intent] = None
#     confidence_scores: Dict[str, float] = Field(default_factory=dict)
#     
#     # Planning state
#     partial_blueprint: Optional[PartialBlueprint] = None
#     decomposition_tree: Optional[Dict[str, Any]] = None
#     
#     # Memory snapshots
#     working_memory_keys: List[str] = Field(default_factory=list)
#     recent_episodes: List[str] = Field(default_factory=list)
#     
#     model_config = ConfigDict(extra="forbid")  # iceOS strict validation 