"""Tests that document the ACTUAL structure of core models.

These are not "contracts" in the protocol/interface sense - they're
documentation tests that show what fields our models REALLY have,
preventing incorrect assumptions in other tests.

When these tests fail, it means our documentation is wrong, not the models!
"""

import pytest
from pydantic import ValidationError

from ice_core.models import (
    LLMOperatorConfig,
    ToolNodeConfig,
    AgentNodeConfig,
    ModelProvider
)
# Import the LLMConfig that LLMOperatorConfig actually uses
from ice_core.models.node_models import LLMConfig


class TestLLMConfigContract:
    """Documents the actual structure of LLMConfig."""
    
    def test_llm_config_fields(self):
        """LLMConfig has these exact fields."""
        # This is the ACTUAL structure - not assumptions!
        config = LLMConfig(
            provider=ModelProvider.OPENAI,
            api_key="sk-test",
            timeout=30,
            max_retries=3
        )
        
        # These are the actual fields that exist
        assert hasattr(config, 'provider')
        assert hasattr(config, 'api_key')
        assert hasattr(config, 'timeout')
        assert hasattr(config, 'max_retries')
        
        # The rich LLMConfig DOES have these fields!
        assert hasattr(config, 'model')  # Rich LLMConfig includes model
        assert hasattr(config, 'temperature')  # And temperature
        assert hasattr(config, 'max_tokens')  # And max_tokens


class TestLLMOperatorConfigContract:
    """Documents the actual structure of LLMOperatorConfig."""
    
    def test_llm_operator_config_fields(self):
        """LLMOperatorConfig has these exact fields."""
        config = LLMOperatorConfig(
            id="test",
            type="llm",
            model="gpt-4",
            prompt="Hello {name}",  # NOT prompt_template!
            llm_config=LLMConfig(provider=ModelProvider.OPENAI),
            temperature=0.7,
            max_tokens=1000
        )
        
        # These are the actual fields
        assert hasattr(config, 'model')
        assert hasattr(config, 'prompt')  # NOT prompt_template!
        assert hasattr(config, 'llm_config')
        assert hasattr(config, 'temperature')
        assert hasattr(config, 'max_tokens')
        
        # Common mistakes - these fields do NOT exist
        assert not hasattr(config, 'prompt_template')  # It's 'prompt'!
        # Note: provider DOES exist from BaseNodeConfig inheritance


class TestAgentNodeConfigContract:
    """Documents the actual structure of AgentNodeConfig."""
    
    def test_agent_node_config_fields(self):
        """AgentNodeConfig uses 'package' not 'agent_ref'."""
        config = AgentNodeConfig(
            id="agent1",
            type="agent", 
            package="ice_sdk.agents.example.ExampleAgent",  # NOT agent_ref!
            tools=[],
            max_iterations=10
        )
        
        # Actual fields
        assert hasattr(config, 'package')  # NOT agent_ref!
        assert hasattr(config, 'tools')
        assert hasattr(config, 'max_iterations')
        
        # Common mistakes
        assert not hasattr(config, 'agent_ref')  # It's 'package'!


class TestNodeConfigValidation:
    """Test that documents validation behavior."""
    
    def test_extra_fields_forbidden(self):
        """Most configs have extra='forbid' - extra fields cause errors."""
        with pytest.raises(ValidationError) as exc_info:
            LLMOperatorConfig(
                id="test",
                type="llm",
                model="gpt-4",
                prompt="test",
                llm_config=LLMConfig(provider=ModelProvider.OPENAI),
                unknown_field="boom"  # This will fail!
            )
        
        assert "Extra inputs are not permitted" in str(exc_info.value) 