"""Central Prometheus metrics registry shared across layers."""

from prometheus_client import Counter

EXEC_STARTED = Counter(
    "executions_started_total",
    "Total number of workflow executions started",
)

EXEC_COMPLETED = Counter(
    "executions_completed_total",
    "Total number of workflow executions finished (success or failure)",
)