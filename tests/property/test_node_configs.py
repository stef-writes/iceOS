from __future__ import annotations

try:
    from hypothesis import given  # type: ignore
    from hypothesis_pydantic import models  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import pytest  # type: ignore

    pytest.skip("Hypothesis not installed", allow_module_level=True)

from ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig


@given(models.from_model(AiNodeConfig))
def test_ai_node_roundtrip(cfg: AiNodeConfig):
    """AiNodeConfig should serialise / deserialise loss-lessly."""

    as_json = cfg.model_dump_json()
    again = AiNodeConfig.model_validate_json(as_json)
    assert cfg == again


@given(models.from_model(ToolNodeConfig))
def test_tool_node_roundtrip(cfg: ToolNodeConfig):
    """ToolNodeConfig should serialise / deserialise loss-lessly."""

    as_json = cfg.model_dump_json()
    again = ToolNodeConfig.model_validate_json(as_json)
    assert cfg == again
