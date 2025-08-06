"""Human trigger tool for triggering human intervention in marketplace conversations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from ice_core.base_tool import ToolBase
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry


class HumanTriggerTool(ToolBase):
    """Trigger human intervention for complex marketplace inquiries."""

    name: str = "human_trigger"
    description: str = "Trigger human intervention for complex marketplace inquiries"

    async def _execute_impl(self, *, reason: str, conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger human intervention.
        
        Args:
            reason: Reason for human intervention
            conversation_context: Current conversation context
            
        Returns:
            Human trigger result
        """
        # Define triggers that require human intervention
        triggers = [
            "price", "discount", "negotiate", "best offer", "deal",
            "delivery", "pickup", "meet", "location", "shipping",
            "condition", "damage", "warranty", "defects",
            "payment", "cash", "deposit", "hold", "reserve",
            "inspection", "test", "try", "see"
        ]
        
        # Check if the reason contains trigger words
        needs_human = any(trigger in reason.lower() for trigger in triggers)
        
        return {
            "triggered": needs_human,
            "reason": reason,
            "conversation_context": conversation_context,
            "timestamp": datetime.utcnow().isoformat(),
            "human_intervention_required": needs_human,
            "priority": "high" if needs_human else "low"
        }


# Auto-registration -----------------------------------------------------------
try:
    _instance = HumanTriggerTool()
    registry.register_instance(NodeType.TOOL, _instance.name, _instance, validate=False)  # type: ignore[arg-type]
except Exception:
    # Tool already registered, skip
    pass 