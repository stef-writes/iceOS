"""Alert management for monitoring."""
from typing import Dict, Any, List
from ice_sdk.services.locator import ServiceLocator

class AlertManager:
    """Manages alert sending for monitoring triggers."""
    
    async def send_alert(
        self, 
        message: str, 
        channels: List[str], 
        context: Dict[str, Any]
    ) -> None:
        """Send alert through configured channels."""
        try:
            # Get alert service from ServiceLocator
            alert_service = ServiceLocator.get("alert_service")
            
            # Send alert through all configured channels
            await alert_service.send_alert(
                message=message,
                channels=channels,
                metadata=context
            )
            
        except Exception as e:
            # Fallback logging if alert service is not available
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send monitoring alert: {e}")
            logger.warning(f"Alert message: {message}")
            logger.warning(f"Alert channels: {channels}")
    
    async def send_escalation_alert(
        self,
        original_message: str,
        escalation_reason: str,
        channels: List[str],
        context: Dict[str, Any]
    ) -> None:
        """Send escalated alert for critical monitoring events."""
        escalated_message = f"ESCALATED: {original_message} | Reason: {escalation_reason}"
        
        # Add escalation metadata
        escalated_context = {
            **context,
            "escalation": True,
            "escalation_reason": escalation_reason,
            "original_message": original_message
        }
        
        await self.send_alert(escalated_message, channels, escalated_context) 