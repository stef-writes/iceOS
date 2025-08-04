"""Central Prometheus metrics registry shared across layers."""

from prometheus_client import Counter, Histogram

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

# ---------------------------------------------------------------------------
# Sandbox resource metrics ---------------------------------------------------
# ---------------------------------------------------------------------------
SANDBOX_CPU_SECONDS = Histogram(
    "sandbox_cpu_seconds",
    "CPU time consumed by tasks executed inside ResourceSandbox",
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30, 60),
)

SANDBOX_MAX_RSS_BYTES = Histogram(
    "sandbox_max_rss_bytes",
    "Maximum resident set size (RSS) in bytes observed for sandboxed tasks",
    buckets=(
        16 * 1024 * 1024,
        32 * 1024 * 1024,
        64 * 1024 * 1024,
        128 * 1024 * 1024,
        256 * 1024 * 1024,
        512 * 1024 * 1024,
        1024 * 1024 * 1024,
    ),
)