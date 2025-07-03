import pytest

pytest.skip(
    "Load/perf benchmarks are skipped in default test run (enable via BENCHMARK env)",
    allow_module_level=True,
)
