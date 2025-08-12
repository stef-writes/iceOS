"""Central metrics registry shared across layers.

Metrics are optional. When ``prometheus_client`` is not installed, all metric
objects degrade to no-ops so imports never fail and unit CI remains lean.
"""

from __future__ import annotations

from typing import (
    Iterable,
    Optional,
    Protocol,
    Sequence,
    Union,
    cast,
    runtime_checkable,
)

from ice_core.models.enums import MetricName

# ----------------------------------------------------------------------------
# Optional Prometheus dependency ---------------------------------------------
# ----------------------------------------------------------------------------

try:  # Attempt to import real Prometheus module
    import prometheus_client as _prom  # type: ignore

    _PROM_AVAILABLE = True
except Exception:  # pragma: no cover – optional dependency
    _prom = None  # type: ignore[assignment]
    _PROM_AVAILABLE = False


@runtime_checkable
class CounterLike(Protocol):
    def labels(self, *args: object, **kwargs: object) -> "CounterLike": ...
    def inc(self, amount: float = 1.0) -> None: ...


@runtime_checkable
class HistogramLike(Protocol):
    def labels(self, *args: object, **kwargs: object) -> "HistogramLike": ...
    def observe(self, value: float) -> None: ...


class _NoOpCounter:
    """Minimal metric stub with Prometheus-like API.

    Provides ``labels(...)`` and ``inc(...)`` that are no-ops.
    """

    # Keep constructor signature compatible with prometheus_client
    def __init__(
        self,
        *_: object,
        **__: object,
    ) -> None:
        pass

    def labels(self, *args: object, **kwargs: object) -> "_NoOpCounter":  # noqa: D401
        return self

    def inc(self, amount: float = 1.0) -> None:  # noqa: D401
        return None


class _NoOpHistogram:
    def __init__(
        self,
        *_: object,
        **__: object,
    ) -> None:
        pass

    def labels(self, *args: object, **kwargs: object) -> "_NoOpHistogram":  # noqa: D401
        return self

    def observe(self, value: float) -> None:  # noqa: D401
        return None


def _make_counter(
    name: str,
    documentation: str,
    *,
    labelnames: Optional[Iterable[str]] = None,
) -> CounterLike:
    if _PROM_AVAILABLE and _prom is not None:  # pragma: no cover - passthrough
        c = _prom.Counter(name, documentation, labelnames=tuple(labelnames or ()))  # type: ignore[misc]
        return cast(CounterLike, c)
    return _NoOpCounter()


def _make_histogram(
    name: str,
    documentation: str,
    *,
    labelnames: Optional[Iterable[str]] = None,
    buckets: Optional[Sequence[Union[float, str]]] = None,
) -> HistogramLike:
    if _PROM_AVAILABLE and _prom is not None:  # pragma: no cover - passthrough
        if buckets is not None:
            h = _prom.Histogram(
                name,
                documentation,
                labelnames=tuple(labelnames or ()),
                buckets=tuple(buckets),
            )  # type: ignore[misc]
        else:
            h = _prom.Histogram(
                name,
                documentation,
                labelnames=tuple(labelnames or ()),
            )  # type: ignore[misc]
        return cast(HistogramLike, h)
    return _NoOpHistogram()


EXEC_STARTED: CounterLike = _make_counter(
    MetricName.EXECUTIONS_STARTED.value,
    "Total number of workflow executions started",
)

EXEC_COMPLETED: CounterLike = _make_counter(
    MetricName.EXECUTIONS_COMPLETED.value,
    "Total number of workflow executions finished (success or failure)",
)

EXEC_FAILED: CounterLike = _make_counter(
    MetricName.EXECUTIONS_FAILED.value,
    "Total number of node executions that ended in failure after retries",
)

LLM_COST_TOTAL: CounterLike = _make_counter(
    MetricName.LLM_COST_TOTAL.value,
    "Accumulated USD cost of LLM calls",
)

DRAFT_MUTATION_TOTAL: CounterLike = _make_counter(
    MetricName.DRAFT_MUTATION_TOTAL.value,
    "Count of draft mutations (lock / position / instantiate)",
    labelnames=["action"],
)

# ---------------------------------------------------------------------------
# Memory metrics -------------------------------------------------------------
# ---------------------------------------------------------------------------
MEMORY_TOKEN_TOTAL: CounterLike = _make_counter(
    "memory_tokens_total",
    "Total number of tokens stored across memory back-ends",
    labelnames=["memory_type"],
)

MEMORY_COST_TOTAL: CounterLike = _make_counter(
    "memory_cost_total",
    "Total estimated USD cost of memory entries",
    labelnames=["memory_type"],
)

# ---------------------------------------------------------------------------
# Sandbox resource metrics ---------------------------------------------------
# ---------------------------------------------------------------------------
SANDBOX_CPU_SECONDS: HistogramLike = _make_histogram(
    "sandbox_cpu_seconds",
    "CPU time consumed by tasks executed inside ResourceSandbox",
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30, 60),
)

SANDBOX_MAX_RSS_BYTES: HistogramLike = _make_histogram(
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
