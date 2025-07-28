"""Human approval workflow handling."""
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from ice_core.models.node_models import HumanNodeConfig

@dataclass
class ApprovalResult:
    """Result of human approval workflow."""
    approved: bool
    response: str
    response_received: bool
    timeout_occurred: bool = False
    escalated: bool = False
    response_time_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "approved": self.approved,
            "response": self.response,
            "response_received": self.response_received,
            "timeout_occurred": self.timeout_occurred,
            "escalated": self.escalated,
            "response_time_seconds": self.response_time_seconds
        }

class ApprovalHandler:
    """Handles human approval workflows with timeouts and escalation."""
    
    def __init__(self, config: HumanNodeConfig):
        self.config = config
        
    async def request_approval(self, inputs: Dict[str, Any]) -> ApprovalResult:
        """Request human approval with timeout and escalation handling."""
        start_time = datetime.utcnow()
        
        # Emit workflow pause event
        await self._pause_workflow_for_human_input(inputs)
        
        try:
            # Wait for human response with timeout
            if self.config.timeout_seconds:
                response = await asyncio.wait_for(
                    self._wait_for_human_response(inputs),
                    timeout=self.config.timeout_seconds
                )
            else:
                response = await self._wait_for_human_response(inputs)
            
            # Calculate response time
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            # Resume workflow
            await self._resume_workflow_from_human_input(response)
            
            return ApprovalResult(
                approved=response.get("approved", False),
                response=response.get("response", ""),
                response_received=True,
                response_time_seconds=response_time
            )
            
        except asyncio.TimeoutError:
            # Handle timeout with auto-approval or escalation
            return await self._handle_timeout(inputs, start_time)
        
    async def _wait_for_human_response(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for human response through event system."""
        # This would integrate with your event system/UI
        # For now, simulate a response based on approval type
        await asyncio.sleep(1)  # Simulate wait time
        
        if self.config.approval_type == "approve_reject":
            return {"approved": True, "response": "Approved"}
        elif self.config.approval_type == "choice" and self.config.choices:
            return {"approved": True, "response": self.config.choices[0]}
        else:
            return {"approved": True, "response": "User input received"}
    
    async def _handle_timeout(
        self, 
        inputs: Dict[str, Any], 
        start_time: datetime
    ) -> ApprovalResult:
        """Handle timeout with auto-approval or escalation."""
        if self.config.auto_approve_after:
            # Auto-approve after specified time
            return ApprovalResult(
                approved=True,
                response="Auto-approved after timeout",
                response_received=False,
                timeout_occurred=True
            )
        elif self.config.escalation_path:
            # Escalate to escalation path
            from .escalation import EscalationManager
            escalation_manager = EscalationManager()
            escalation_result = await escalation_manager.escalate(
                self.config.escalation_path, inputs
            )
            
            return ApprovalResult(
                approved=escalation_result.get("approved", False),
                response=escalation_result.get("response", "Escalated"),
                response_received=True,
                escalated=True,
                timeout_occurred=True
            )
        else:
            # Timeout with no auto-approval or escalation - reject
            return ApprovalResult(
                approved=False,
                response="Timeout - no response received",
                response_received=False,
                timeout_occurred=True
            )
    
    async def _pause_workflow_for_human_input(self, inputs: Dict[str, Any]) -> None:
        """Pause workflow execution for human input."""
        # This would integrate with your workflow event system
        pass
    
    async def _resume_workflow_from_human_input(self, response: Dict[str, Any]) -> None:
        """Resume workflow execution after human input."""
        # This would integrate with your workflow event system
        pass 