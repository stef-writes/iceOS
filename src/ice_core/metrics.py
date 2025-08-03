"""Central Prometheus metrics registry shared across layers."""

from prometheus_client import Counter

from ice_core.models.enums import MetricName

EXEC_STARTED = Counter(
    MetricName.EXECUTIONS_STARTED.value,
    "Total number of workflow executions started",
)

EXEC_COMPLETED = Counter(
    MetricName.EXECUTIONS_COMPLETED.value,
    "Total number of workflow executions finished (success or failure)",
)

EXEC_FAILED = Counter(
    MetricName.EXECUTIONS_FAILED.value,
    "Total number of node executions that ended in failure after retries",
)

LLM_COST_TOTAL = Counter(
    MetricName.LLM_COST_TOTAL.value,
    "Accumulated USD cost of LLM calls",
)

DRAFT_MUTATION_TOTAL = Counter(
    MetricName.DRAFT_MUTATION_TOTAL.value,
    "Count of draft mutations (lock / position / instantiate)",
    labelnames=["action"],
)

# ---------------------------------------------------------------------------
# Memory metrics -------------------------------------------------------------
# ---------------------------------------------------------------------------
MEMORY_TOKEN_TOTAL = Counter(
    "memory_tokens_total",
    "Total number of tokens stored across memory back-ends",
    labelnames=["memory_type"],
)

MEMORY_COST_TOTAL = Counter(
    "memory_cost_total",
    "Total estimated USD cost of memory entries",
    labelnames=["memory_type"],
)