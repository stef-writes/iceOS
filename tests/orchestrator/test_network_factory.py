from pathlib import Path

import pytest
import yaml

from ice_orchestrator.core.network_factory import NetworkFactory


@pytest.mark.asyncio
async def test_network_factory_from_yaml(tmp_path: Path):
    """NetworkFactory must build a ScriptChain from YAML spec."""

    spec = {
        "metadata": {
            "name": "simple-chain",
            "version": "1.0.0",
            "description": "Test chain",
            "tags": [],
        },
        "nodes": {
            "n1": {
                "type": "tool",
                "tool_name": "dummy",
                "dependencies": [],
            },
            "n2": {
                "type": "tool",
                "tool_name": "dummy",
                "dependencies": ["n1"],
            },
        },
    }

    path = tmp_path / "chain.yaml"
    path.write_text(yaml.safe_dump(spec))

    chain = await NetworkFactory.from_yaml(path)

    # Monkey-patch context_manager.execute_tool so tool executor succeeds
    async def _dummy(*args, **kwargs):  # noqa: D401
        return {"ok": True}

    original_execute_tool = chain.context_manager.execute_tool  # type: ignore[assignment]

    chain.context_manager.execute_tool = _dummy  # type: ignore[assignment]

    assert chain.get_node_level("n1") == 0
    assert chain.get_node_level("n2") == 1

    result = await chain.execute()

    # Restore original method to avoid leaking across tests
    chain.context_manager.execute_tool = original_execute_tool  # type: ignore[assignment]

    assert result.success is True
