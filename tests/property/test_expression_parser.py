# pyright: basic
import asyncio
from typing import Any

try:
    from hypothesis import given
    from hypothesis import strategies as st  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import pytest  # type: ignore

    pytest.skip("Hypothesis not installed", allow_module_level=True)

from ice_sdk.executors.condition import condition_executor
from ice_sdk.models.node_models import ConditionNodeConfig

simple_exprs = st.sampled_from(
    [
        "x > y",
        "value == 42",
        "flag and (score < limit)",
    ]
)


@given(
    expr=simple_exprs,
    x=st.integers(),
    y=st.integers(),
    value=st.integers(),
    flag=st.booleans(),
    score=st.integers(),
    limit=st.integers(),
)
def test_expression_matches_eval(expr: str, **ctx: Any):
    """Expression evaluated by executor matches Python eval result."""

    cfg = ConditionNodeConfig(id="cond-1", name="test", type="condition", expression=expr)  # type: ignore[arg-type]

    # Run executor synchronously via asyncio
    result = asyncio.run(condition_executor(chain=None, cfg=cfg, ctx=ctx))  # type: ignore[arg-type]

    assert result.success
    expected = eval(
        expr, {"__builtins__": {}}, ctx
    )  # noqa: S307 (evaluated in sandbox)
    assert result.output["result"] == bool(expected)  # type: ignore[index]
