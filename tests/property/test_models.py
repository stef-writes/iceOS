try:
    from hypothesis import given  # type: ignore
    from hypothesis_pydantic import models  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import pytest  # type: ignore

    pytest.skip("Hypothesis not installed", allow_module_level=True)

from ice_sdk.models.node_models import ConditionNodeConfig


@given(models.from_model(ConditionNodeConfig))
def test_condition_node_roundtrip(cfg: ConditionNodeConfig):
    """Serialise → JSON → model should round-trip loss-lessly."""

    as_json = cfg.model_dump_json()
    again = ConditionNodeConfig.model_validate_json(as_json)

    assert cfg == again 