"""Alert service for iceOS monitoring and notification system.

Provides enterprise-grade alerting capabilities that integrate with the
ServiceLocator pattern and support multiple notification channels.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

import structlog

logger = structlog.get_logger(__name__)


class AlertChannel(str, Enum):
    """Supported alert channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    DASHBOARD = "dashboard"
    LOG = "log"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertNotificationProtocol(Protocol):
    """Protocol for alert notification handlers."""
    
    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any]
    ) -> bool:
        """Send alert through specific channel."""
        ...


class EmailAlertHandler:
    """Email alert notification handler."""
    
    def __init__(self, smtp_config: Optional[Dict[str, Any]] = None):
        self.smtp_config = smtp_config or {}
        
    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any]
    ) -> bool:
        """Send email alert."""
        try:
            # TODO: Integrate with actual email service
            logger.info(
                "EMAIL ALERT",
                message=message,
                severity=severity.value,
                metadata=metadata
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False


class SlackAlertHandler:
    """Slack alert notification handler."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        
    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any]
    ) -> bool:
        """Send Slack alert."""
        try:
            # TODO: Integrate with actual Slack webhook
            severity_emoji = {
                AlertSeverity.LOW: "🟡",
                AlertSeverity.MEDIUM: "🟠", 
                AlertSeverity.HIGH: "🔴",
                AlertSeverity.CRITICAL: "🚨"
            }
            
            slack_message = f"{severity_emoji.get(severity, '🔵')} {message}"
            
            logger.info(
                "SLACK ALERT",
                message=slack_message,
                severity=severity.value,
                metadata=metadata,
                webhook_url=self.webhook_url
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False


class WebhookAlertHandler:
    """Generic webhook alert notification handler."""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}
        
    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any]
    ) -> bool:
        """Send webhook alert."""
        try:
            payload = {
                "message": message,
                "severity": severity.value,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata
            }
            
            # TODO: Integrate with actual HTTP client
            logger.info(
                "WEBHOOK ALERT",
                webhook_url=self.webhook_url,
                payload=payload,
                headers=self.headers
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


class LogAlertHandler:
    """Log-based alert handler for development and debugging."""
    
    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any]
    ) -> bool:
        """Send log alert."""
        try:
            log_level = {
                AlertSeverity.LOW: "info",
                AlertSeverity.MEDIUM: "warning",
                AlertSeverity.HIGH: "error",
                AlertSeverity.CRITICAL: "critical"
            }.get(severity, "info")
            
            getattr(logger, log_level)(
                f"🚨 ALERT: {message}",
                severity=severity.value,
                metadata=metadata
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send log alert: {e}")
            return False


class AlertService:
    """Centralized alert service for iceOS monitoring system."""
    
    def __init__(self):
        self._handlers: Dict[AlertChannel, AlertNotificationProtocol] = {}
        self._initialize_default_handlers()
        
    def _initialize_default_handlers(self) -> None:
        """Initialize default alert handlers."""
        # Always available log handler
        self._handlers[AlertChannel.LOG] = LogAlertHandler()
        
    def register_handler(
        self,
        channel: AlertChannel,
        handler: AlertNotificationProtocol
    ) -> None:
        """Register an alert handler for a specific channel."""
        self._handlers[channel] = handler
        logger.info(f"Registered alert handler for {channel.value}")
        
    def configure_email_alerts(
        self,
        smtp_config: Dict[str, Any]
    ) -> None:
        """Configure email alert handler."""
        self._handlers[AlertChannel.EMAIL] = EmailAlertHandler(smtp_config)
        
    def configure_slack_alerts(
        self,
        webhook_url: str
    ) -> None:
        """Configure Slack alert handler."""
        self._handlers[AlertChannel.SLACK] = SlackAlertHandler(webhook_url)
        
    def configure_webhook_alerts(
        self,
        webhook_url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        """Configure webhook alert handler."""
        self._handlers[AlertChannel.WEBHOOK] = WebhookAlertHandler(webhook_url, headers)
        
    async def send_alert(
        self,
        message: str,
        channels: List[str],
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """Send alert through multiple channels.
        
        Args:
            message: Alert message
            channels: List of channel names to send to
            severity: Alert severity level
            metadata: Additional metadata to include
            
        Returns:
            Dict mapping channel names to success status
        """
        metadata = metadata or {}
        results = {}
        
        # Convert string channels to enum values
        channel_enums = []
        for channel_str in channels:
            try:
                channel_enum = AlertChannel(channel_str.lower())
                channel_enums.append(channel_enum)
            except ValueError:
                logger.warning(f"Unknown alert channel: {channel_str}")
                results[channel_str] = False
                
        # Send alerts in parallel
        tasks = []
        for channel in channel_enums:
            handler = self._handlers.get(channel)
            if handler:
                task = asyncio.create_task(
                    handler.send_alert(message, severity, metadata)
                )
                tasks.append((channel.value, task))
            else:
                logger.warning(f"No handler registered for {channel.value}")
                results[channel.value] = False
                
        # Wait for all alerts to complete
        if tasks:
            completed_tasks = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )
            
            for (channel_name, _), result in zip(tasks, completed_tasks):
                if isinstance(result, Exception):
                    logger.error(f"Alert failed for {channel_name}: {result}")
                    results[channel_name] = False
                else:
                    results[channel_name] = bool(result)
                    
        return results
        
    async def send_monitoring_alert(
        self,
        node_id: str,
        metric_expression: str,
        trigger_values: Dict[str, Any],
        channels: List[str],
        workflow_id: Optional[str] = None
    ) -> Dict[str, bool]:
        """Send monitoring-specific alert.
        
        Convenience method for monitor nodes to send formatted alerts.
        """
        severity = self._determine_severity(trigger_values)
        
        message = f"Monitoring condition triggered on node '{node_id}': {metric_expression}"
        
        metadata = {
            "node_id": node_id,
            "metric_expression": metric_expression,
            "trigger_values": trigger_values,
            "workflow_id": workflow_id,
            "alert_type": "monitoring",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_alert(message, channels, severity, metadata)
        
    def _determine_severity(self, trigger_values: Dict[str, Any]) -> AlertSeverity:
        """Determine alert severity based on trigger values."""
        # Simple heuristic - can be enhanced with configuration
        cost = trigger_values.get("cost", 0)
        latency = trigger_values.get("latency", 0)
        
        if cost > 1000 or latency > 120:
            return AlertSeverity.CRITICAL
        elif cost > 500 or latency > 60:
            return AlertSeverity.HIGH
        elif cost > 100 or latency > 30:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
            
    def get_supported_channels(self) -> List[str]:
        """Get list of supported alert channels."""
        return [channel.value for channel in AlertChannel]
        
    def get_active_channels(self) -> List[str]:
        """Get list of currently configured alert channels."""
        return list(self._handlers.keys())


# Global instance for ServiceLocator integration
_alert_service: Optional[AlertService] = None


async def get_alert_service() -> AlertService:
    """Get or create the global alert service instance."""
    global _alert_service
    
    if _alert_service is None:
        _alert_service = AlertService()
        
        # Register with ServiceLocator for dependency injection
        try:
            from ice_core.services.contracts import ServiceLocator
            ServiceLocator.register("alert_service", _alert_service)
            logger.info("Alert service registered with ServiceLocator")
        except ImportError:
            logger.warning("ServiceLocator not available - alert service running standalone")
            
    return _alert_service


async def configure_production_alerts(
    email_config: Optional[Dict[str, Any]] = None,
    slack_webhook: Optional[str] = None,
    custom_webhook: Optional[str] = None
) -> AlertService:
    """Configure alert service for production use.
    
    Convenience function to set up common production alert channels.
    """
    alert_service = await get_alert_service()
    
    if email_config:
        alert_service.configure_email_alerts(email_config)
        
    if slack_webhook:
        alert_service.configure_slack_alerts(slack_webhook)
        
    if custom_webhook:
        alert_service.configure_webhook_alerts(custom_webhook)
        
    logger.info("Alert service configured for production")
    return alert_service 