"""Unit tests for :pymod:`src.frosty` canonical package."""

from src.frosty import FlowDesignAgent, FrostyContext, NodeBuilderAgent
from src.frosty.agents.flow_design.assistant import (
    FlowDesignAgent as FlowDesignAgentDirect,
)
from src.frosty.agents.node_builder.builder import (
    NodeBuilderAgent as NodeBuilderAgentDirect,
)


def test_frosty_context_initialization() -> None:
    """Test that FrostyContext can be initialized."""
    context = FrostyContext()
    assert context is not None
    assert hasattr(context, "agents")
    assert hasattr(context, "memory")


def test_flow_design_agent_import() -> None:
    """Test that FlowDesignAgent can be imported and instantiated."""
    agent = FlowDesignAgent()
    assert agent is not None
    assert hasattr(agent, "run")


def test_node_builder_agent_import() -> None:
    """Test that NodeBuilderAgent can be imported and instantiated."""
    agent = NodeBuilderAgent()
    assert agent is not None
    assert hasattr(agent, "run")


def test_direct_imports_work() -> None:
    """Test that direct imports from submodules work."""
    flow_agent = FlowDesignAgentDirect()
    builder_agent = NodeBuilderAgentDirect()

    assert flow_agent is not None
    assert builder_agent is not None
