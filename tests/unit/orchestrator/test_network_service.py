import pytest
from ice_core.exceptions import SpecConflictError

from ice_sdk.models.network import NetworkSpec
from ice_sdk.services.network_service import NetworkService


class TestNetworkService:
    async def test_create_network_spec_conflict(self):
        spec = NetworkSpec(id="test", node_ids=["node.test"])
        await NetworkService().create_network_spec(spec)
        
        with pytest.raises(SpecConflictError):
            await NetworkService().create_network_spec(spec)

    async def test_list_specs_with_filter(self):
        service = NetworkService()
        # ... test filter logic ...