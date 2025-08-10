"""Resource monitoring and limits for WASM execution.

Provides comprehensive monitoring of CPU, memory, and execution time
with OpenTelemetry integration for observability.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import structlog
from opentelemetry import metrics, trace  # type: ignore[import-not-found]
from opentelemetry.trace import Status, StatusCode  # type: ignore[import-not-found]

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)
logger = structlog.get_logger(__name__)

# Metrics for WASM execution monitoring
execution_counter = meter.create_counter(
    "wasm_executions_total", description="Total number of WASM executions", unit="1"
)

execution_duration = meter.create_histogram(
    "wasm_execution_duration_seconds",
    description="Duration of WASM executions",
    unit="s",
)

memory_usage = meter.create_histogram(
    "wasm_memory_usage_pages",
    description="Memory usage during WASM execution",
    unit="pages",
)

fuel_consumption = meter.create_histogram(
    "wasm_fuel_consumption",
    description="CPU fuel consumed during WASM execution",
    unit="fuel",
)

resource_limit_violations = meter.create_counter(
    "wasm_resource_limit_violations_total",
    description="Number of resource limit violations",
    unit="1",
)


@dataclass
class ResourceLimits:
    """Resource limits for WASM execution."""

    memory_pages: int  # Memory limit in 64KB pages
    fuel: int  # CPU fuel limit
    timeout: float  # Execution timeout in seconds
    max_file_size: int = 1024 * 1024  # 1MB file size limit
    max_network_calls: int = 0  # No network calls by default


@dataclass
class ResourceUsage:
    """Resource usage during WASM execution."""

    memory_pages_used: int
    fuel_consumed: int
    execution_time: float
    start_time: datetime
    end_time: datetime
    file_operations: int = 0
    network_calls: int = 0

    @property
    def memory_mb(self) -> float:
        """Convert pages to MB."""
        return self.memory_pages_used * 64 / 1024


@dataclass
class SecurityViolation:
    """Security violation detected during execution."""

    violation_type: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    timestamp: datetime
    node_id: str
    node_type: str


class WasmResourceMonitor:
    """Comprehensive resource monitoring for WASM execution."""

    def __init__(self) -> None:
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self.violation_callbacks: List[Callable[[SecurityViolation], None]] = []

    def add_violation_callback(
        self, callback: Callable[[SecurityViolation], None]
    ) -> None:
        """Add a callback for security violations."""
        self.violation_callbacks.append(callback)

    async def monitor_execution(
        self,
        node_id: str,
        node_type: str,
        limits: ResourceLimits,
        execution_func: Callable[[], Any],
    ) -> tuple[Any, ResourceUsage]:
        """Monitor a WASM execution with comprehensive resource tracking."""

        execution_id = f"{node_id}_{int(time.time())}"
        start_time = datetime.utcnow()

        with tracer.start_as_current_span(
            "wasm.monitor_execution",
            attributes={
                "node_id": node_id,
                "node_type": node_type,
                "memory_limit_pages": limits.memory_pages,
                "fuel_limit": limits.fuel,
                "timeout_seconds": limits.timeout,
            },
        ) as span:

            # Track active execution
            self.active_executions[execution_id] = {
                "node_id": node_id,
                "node_type": node_type,
                "start_time": start_time,
                "limits": limits,
            }

            try:
                # Execute with monitoring
                execution_start = time.perf_counter()

                result = await asyncio.wait_for(
                    execution_func(), timeout=limits.timeout
                )

                execution_end = time.perf_counter()
                end_time = datetime.utcnow()
                duration = execution_end - execution_start

                # Extract resource usage from result
                usage = self._extract_resource_usage(
                    result, start_time, end_time, duration
                )

                # Check for violations
                await self._check_violations(node_id, node_type, limits, usage)

                # Record metrics
                self._record_metrics(node_type, usage, "success")

                # Update span
                span.set_attribute("execution_time", duration)
                span.set_attribute("memory_used_pages", usage.memory_pages_used)
                span.set_attribute("fuel_consumed", usage.fuel_consumed)
                span.set_status(Status(StatusCode.OK))

                logger.info(
                    "WASM execution monitored successfully",
                    node_id=node_id,
                    node_type=node_type,
                    duration=duration,
                    memory_mb=usage.memory_mb,
                    fuel_consumed=usage.fuel_consumed,
                )

                return result, usage

            except asyncio.TimeoutError:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                violation = SecurityViolation(
                    violation_type="timeout",
                    description=f"Execution exceeded timeout of {limits.timeout}s",
                    severity="high",
                    timestamp=end_time,
                    node_id=node_id,
                    node_type=node_type,
                )
                await self._handle_violation(violation)

                self._record_metrics(node_type, None, "timeout")
                span.set_status(Status(StatusCode.ERROR, "Timeout"))

                raise

            except Exception as e:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                violation = SecurityViolation(
                    violation_type="execution_error",
                    description=f"Execution failed: {str(e)}",
                    severity="medium",
                    timestamp=end_time,
                    node_id=node_id,
                    node_type=node_type,
                )
                await self._handle_violation(violation)

                self._record_metrics(node_type, None, "error")
                span.set_status(Status(StatusCode.ERROR, str(e)))

                raise

            finally:
                # Clean up tracking
                self.active_executions.pop(execution_id, None)

    def _extract_resource_usage(
        self, result: Any, start_time: datetime, end_time: datetime, duration: float
    ) -> ResourceUsage:
        """Extract resource usage from execution result."""

        # Default usage
        usage = ResourceUsage(
            memory_pages_used=0,
            fuel_consumed=0,
            execution_time=duration,
            start_time=start_time,
            end_time=end_time,
        )

        # Extract from result if available
        if hasattr(result, "output") and isinstance(result.output, dict):
            output = result.output
            usage.memory_pages_used = output.get("memory_used_pages", 0)
            usage.fuel_consumed = output.get("fuel_consumed", 0)
            usage.file_operations = output.get("file_operations", 0)
            usage.network_calls = output.get("network_calls", 0)

        return usage

    async def _check_violations(
        self, node_id: str, node_type: str, limits: ResourceLimits, usage: ResourceUsage
    ) -> None:
        """Check for resource limit violations."""

        violations = []

        # Memory violation
        if usage.memory_pages_used > limits.memory_pages:
            violations.append(
                SecurityViolation(
                    violation_type="memory_limit",
                    description=f"Memory usage {usage.memory_pages_used} pages exceeds limit {limits.memory_pages}",
                    severity="high",
                    timestamp=usage.end_time,
                    node_id=node_id,
                    node_type=node_type,
                )
            )

        # CPU violation
        if usage.fuel_consumed > limits.fuel:
            violations.append(
                SecurityViolation(
                    violation_type="cpu_limit",
                    description=f"Fuel consumption {usage.fuel_consumed} exceeds limit {limits.fuel}",
                    severity="high",
                    timestamp=usage.end_time,
                    node_id=node_id,
                    node_type=node_type,
                )
            )

        # Network violation
        if usage.network_calls > limits.max_network_calls:
            violations.append(
                SecurityViolation(
                    violation_type="network_limit",
                    description=f"Network calls {usage.network_calls} exceeds limit {limits.max_network_calls}",
                    severity="critical",
                    timestamp=usage.end_time,
                    node_id=node_id,
                    node_type=node_type,
                )
            )

        # Handle all violations
        for violation in violations:
            await self._handle_violation(violation)

    async def _handle_violation(self, violation: SecurityViolation) -> None:
        """Handle a security violation."""

        logger.warning(
            "Security violation detected",
            violation_type=violation.violation_type,
            description=violation.description,
            severity=violation.severity,
            node_id=violation.node_id,
            node_type=violation.node_type,
        )

        # Record violation metric
        resource_limit_violations.add(
            1,
            attributes={
                "violation_type": violation.violation_type,
                "severity": violation.severity,
                "node_type": violation.node_type,
            },
        )

        # Notify callbacks
        for callback in self.violation_callbacks:
            try:
                callback(violation)
            except Exception as e:
                logger.error(
                    "Violation callback failed",
                    error=str(e),
                    violation_type=violation.violation_type,
                )

    def _record_metrics(
        self, node_type: str, usage: Optional[ResourceUsage], status: str
    ) -> None:
        """Record execution metrics."""

        # Execution counter
        execution_counter.add(1, attributes={"node_type": node_type, "status": status})

        if usage:
            # Duration histogram
            execution_duration.record(
                usage.execution_time, attributes={"node_type": node_type}
            )

            # Memory histogram
            memory_usage.record(
                usage.memory_pages_used, attributes={"node_type": node_type}
            )

            # Fuel histogram
            fuel_consumption.record(
                usage.fuel_consumed, attributes={"node_type": node_type}
            )

    def get_active_executions(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active executions."""
        return self.active_executions.copy()

    async def terminate_execution(
        self, execution_id: str, reason: str = "manual"
    ) -> None:
        """Terminate an active execution."""

        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]

            violation = SecurityViolation(
                violation_type="termination",
                description=f"Execution terminated: {reason}",
                severity="medium",
                timestamp=datetime.utcnow(),
                node_id=execution["node_id"],
                node_type=execution["node_type"],
            )

            await self._handle_violation(violation)

            # Remove from tracking
            self.active_executions.pop(execution_id, None)

            logger.info(
                "Execution terminated",
                execution_id=execution_id,
                reason=reason,
                node_id=execution["node_id"],
            )


# Global resource monitor instance
resource_monitor = WasmResourceMonitor()
