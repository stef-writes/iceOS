import pytest

from ice_core.services.contracts import NodeService, ServiceContract

pytestmark = [pytest.mark.unit]


def test_node_service_happy(monkeypatch):
    # Default load_current returns valid contract
    svc = NodeService("ice_api")
    assert svc._contract.name == "ice_api"  # type: ignore[attr-defined]


def test_node_service_invalid_contract(monkeypatch):
    # Monkeypatch load_current to return empty version
    monkeypatch.setattr(
        "ice_core.services.contracts.load_current",
        lambda _: ServiceContract(version="", name="bad"),
    )

    with pytest.raises(ValueError):
        NodeService("bad") 