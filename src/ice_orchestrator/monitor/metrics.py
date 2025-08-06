"""Metrics evaluation for monitoring."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from ice_core.models.node_models import MonitorNodeConfig
from ice_core.utils.safe_eval import safe_eval_bool


@dataclass
class MonitoringResult:
    """Result of monitoring execution."""

    monitoring_active: bool
    checks_performed: int
    triggers_fired: int
    alerts_sent: int
    action_taken: str
    final_status: str
    monitoring_duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "monitoring_active": self.monitoring_active,
            "checks_performed": self.checks_performed,
            "triggers_fired": self.triggers_fired,
            "alerts_sent": self.alerts_sent,
            "action_taken": self.action_taken,
            "final_status": self.final_status,
            "monitoring_duration_seconds": self.monitoring_duration_seconds,
        }


class MetricsEvaluator:
    """Evaluates monitoring metrics and triggers actions."""

    def __init__(self, config: MonitorNodeConfig):
        self.config = config
        self._monitoring_active = False

    async def monitor(self, inputs: Dict[str, Any]) -> MonitoringResult:
        """Execute monitoring with metric evaluation."""
        start_time = datetime.utcnow()
        checks_performed = 0
        triggers_fired = 0
        alerts_sent = 0
        action_taken = "none"

        self._monitoring_active = True

        try:
            # Start monitoring loop
            while self._monitoring_active:
                checks_performed += 1

                # Evaluate metric expression
                triggered = await self._evaluate_metric_expression(inputs)

                if triggered:
                    triggers_fired += 1

                    # Send alerts if configured
                    if self.config.alert_channels:
                        await self._send_alerts(inputs)
                        alerts_sent += 1

                    # Take action based on configuration
                    if self.config.action_on_trigger == "pause":
                        await self._pause_workflow()
                        action_taken = "workflow_paused"
                        break
                    elif self.config.action_on_trigger == "abort":
                        await self._abort_workflow()
                        action_taken = "workflow_aborted"
                        break
                    else:  # alert_only
                        action_taken = "alert_sent"

                # Wait for next check interval
                await asyncio.sleep(self.config.check_interval_seconds)

                # For demo purposes, break after a few checks
                if checks_performed >= 5:
                    break

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            return MonitoringResult(
                monitoring_active=False,
                checks_performed=checks_performed,
                triggers_fired=triggers_fired,
                alerts_sent=alerts_sent,
                action_taken=action_taken,
                final_status="completed",
                monitoring_duration_seconds=duration,
            )

        except Exception as e:
            return MonitoringResult(
                monitoring_active=False,
                checks_performed=checks_performed,
                triggers_fired=triggers_fired,
                alerts_sent=alerts_sent,
                action_taken="error",
                final_status=f"error: {str(e)}",
            )

    async def _evaluate_metric_expression(self, context: Dict[str, Any]) -> bool:
        """Evaluate the metric expression against current context."""
        try:
            # Create safe evaluation context
            safe_dict: Dict[str, Any] = {"__builtins__": {}}

            # Add workflow metrics
            if "workflow_metrics" in context:
                safe_dict.update(context["workflow_metrics"])

            # Add monitoring context
            if "monitoring_context" in context:
                safe_dict.update(context["monitoring_context"])

            # For demo, add some sample metrics
            safe_dict.update(
                {
                    "cost": 25.50,
                    "latency": 15.2,
                    "error_rate": 0.02,
                    "memory_usage": 0.75,
                }
            )

            # Evaluate expression
            result = safe_eval_bool(self.config.metric_expression, safe_dict)
            return result

        except Exception:
            # If expression evaluation fails, don't trigger
            return False

    async def _send_alerts(self, context: Dict[str, Any]) -> None:
        """Send alerts through configured channels."""
        from .alerting import AlertManager

        alert_manager = AlertManager()
        await alert_manager.send_alert(
            message=f"Monitoring trigger fired: {self.config.metric_expression}",
            channels=self.config.alert_channels,
            context=context,
        )

    async def _pause_workflow(self) -> None:
        """Pause the workflow execution."""
        # This would integrate with your workflow control system
        self._monitoring_active = False

    async def _abort_workflow(self) -> None:
        """Abort the workflow execution."""
        # This would integrate with your workflow control system
        self._monitoring_active = False
