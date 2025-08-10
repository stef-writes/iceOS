"""Tests for new Phase 2 node configuration models."""

import pytest

from ice_core.models import (
    AgentSpec,
    HumanNodeConfig,
    MonitorNodeConfig,
    SwarmNodeConfig,
)

pytestmark = [pytest.mark.unit]


def test_agent_spec_creation():
    """AgentSpec creates with required fields."""
    spec = AgentSpec(package="test.agent", role="analyst")

    assert spec.package == "test.agent"
    assert spec.role == "analyst"
    assert spec.config_overrides == {}


def test_agent_spec_with_overrides():
    """AgentSpec accepts config overrides."""
    spec = AgentSpec(
        package="test.agent", role="analyst", config_overrides={"temperature": 0.8}
    )

    assert spec.config_overrides == {"temperature": 0.8}


def test_swarm_config_basic():
    """SwarmNodeConfig creates with minimum required fields."""
    agents = [
        AgentSpec(package="analyst", role="financial_analyst"),
        AgentSpec(package="critic", role="risk_assessor"),
    ]

    config = SwarmNodeConfig(id="test_swarm", agents=agents)

    assert config.type == "swarm"
    assert len(config.agents) == 2
    assert config.coordination_strategy == "consensus"  # default


def test_swarm_runtime_validation_success():
    """SwarmNodeConfig passes validation with valid agents."""
    agents = [
        AgentSpec(package="analyst", role="financial_analyst"),
        AgentSpec(package="critic", role="risk_assessor"),
    ]

    config = SwarmNodeConfig(id="test_swarm", agents=agents)
    config.runtime_validate()  # Should not raise


def test_swarm_pydantic_validation_insufficient_agents():
    """SwarmNodeConfig fails Pydantic validation with too few agents."""
    agents = [AgentSpec(package="analyst", role="analyst")]

    with pytest.raises(Exception):  # Pydantic ValidationError
        SwarmNodeConfig(id="test_swarm", agents=agents)


def test_swarm_runtime_validation_duplicate_roles():
    """SwarmNodeConfig fails runtime validation with duplicate roles."""
    agents = [
        AgentSpec(package="agent1", role="analyst"),
        AgentSpec(package="agent2", role="analyst"),  # Duplicate role
    ]

    config = SwarmNodeConfig(id="test_swarm", agents=agents)

    with pytest.raises(ValueError):
        config.runtime_validate()


def test_swarm_runtime_validation_empty_package():
    """SwarmNodeConfig fails validation with empty package."""
    agents = [
        AgentSpec(package="", role="analyst"),
        AgentSpec(package="critic", role="critic"),
    ]

    config = SwarmNodeConfig(id="test_swarm", agents=agents)

    with pytest.raises(ValueError):
        config.runtime_validate()


def test_swarm_coordination_strategies():
    """SwarmNodeConfig accepts all valid coordination strategies."""
    agents = [
        AgentSpec(package="agent1", role="role1"),
        AgentSpec(package="agent2", role="role2"),
    ]

    for strategy in ["consensus", "hierarchical", "marketplace"]:
        config = SwarmNodeConfig(
            id="test_swarm", agents=agents, coordination_strategy=strategy
        )
        assert config.coordination_strategy == strategy


def test_human_config_basic():
    """HumanNodeConfig creates with minimum required fields."""
    config = HumanNodeConfig(
        id="test_human", prompt_message="Please approve this action"
    )

    assert config.type == "human"
    assert config.prompt_message == "Please approve this action"
    assert config.approval_type == "approve_reject"  # default


def test_human_runtime_validation_success():
    """HumanNodeConfig passes validation with valid prompt."""
    config = HumanNodeConfig(id="test_human", prompt_message="Please approve")
    config.runtime_validate()  # Should not raise


def test_human_runtime_validation_empty_prompt():
    """HumanNodeConfig fails validation with empty prompt."""
    # Pydantic field validation prevents creation with empty string
    with pytest.raises(Exception):  # Pydantic validation error
        HumanNodeConfig(id="test_human", prompt_message="")


def test_human_runtime_validation_choice_without_choices():
    """HumanNodeConfig fails validation for choice type without choices."""
    config = HumanNodeConfig(
        id="test_human", prompt_message="Choose option", approval_type="choice"
    )

    with pytest.raises(ValueError):
        config.runtime_validate()


def test_human_approval_types():
    """HumanNodeConfig accepts all valid approval types."""
    for approval_type in ["approve_reject", "input_required", "choice"]:
        config = HumanNodeConfig(
            id="test_human",
            prompt_message="Test prompt",
            approval_type=approval_type,
            choices=["yes", "no"] if approval_type == "choice" else None,
        )
        assert config.approval_type == approval_type


def test_monitor_config_basic():
    """MonitorNodeConfig creates with minimum required fields."""
    config = MonitorNodeConfig(id="test_monitor", metric_expression="cost > 100")

    assert config.type == "monitor"
    assert config.metric_expression == "cost > 100"
    assert config.action_on_trigger == "alert_only"  # default


def test_monitor_runtime_validation_success():
    """MonitorNodeConfig passes validation with valid expression."""
    config = MonitorNodeConfig(id="test_monitor", metric_expression="cost > 100")
    config.runtime_validate()  # Should not raise


def test_monitor_runtime_validation_empty_expression():
    """MonitorNodeConfig fails validation with empty expression."""
    # Pydantic field validation prevents creation with empty string
    with pytest.raises(Exception):  # Pydantic validation error
        MonitorNodeConfig(id="test_monitor", metric_expression="")


def test_monitor_runtime_validation_invalid_syntax():
    """MonitorNodeConfig fails validation with invalid syntax."""
    config = MonitorNodeConfig(
        id="test_monitor", metric_expression="cost > > 100"  # Invalid syntax
    )

    with pytest.raises(ValueError):
        config.runtime_validate()


def test_monitor_action_types():
    """MonitorNodeConfig accepts all valid action types."""
    for action in ["pause", "abort", "alert_only"]:
        config = MonitorNodeConfig(
            id="test_monitor", metric_expression="cost > 100", action_on_trigger=action
        )
        assert config.action_on_trigger == action


def test_all_new_node_types_have_consistent_base():
    """All new node configs inherit from BaseNodeConfig properly."""
    swarm_config = SwarmNodeConfig(
        id="test_swarm",
        agents=[
            AgentSpec(package="agent1", role="role1"),
            AgentSpec(package="agent2", role="role2"),
        ],
    )

    human_config = HumanNodeConfig(id="test_human", prompt_message="Test")
    monitor_config = MonitorNodeConfig(
        id="test_monitor", metric_expression="cost > 100"
    )

    for config in [swarm_config, human_config, monitor_config]:
        assert hasattr(config, "id")
        assert hasattr(config, "type")
        assert hasattr(config, "runtime_validate")
        assert callable(config.runtime_validate)
