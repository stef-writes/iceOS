"""Test LLM provider protocol compliance."""
from __future__ import annotations

import pytest
from typing import List

from ice_core.models.llm import LLMConfig, ModelProvider
from ice_core.protocols.llm import ILLMProvider, llm_provider_registry
import os, pytest

if not os.getenv("ENABLE_NL_GENERATOR"):
    pytest.skip("NL generator disabled", allow_module_level=True)


class TestLLMProviderProtocol:
    """Test that all LLM providers properly implement the ILLMProvider protocol."""
    
    def test_protocol_abstract_methods(self):
        """Test that ILLMProvider has all required abstract methods."""
        required_methods = {
            'create',
            'stream_response', 
            'complete',
            'get_cost_estimate',
            'supported_models',
            'get_provider_name',
            'validate_config',
            'model_identifier'
        }
        
        # Check that all required methods are abstract
        abstract_methods = ILLMProvider.__abstractmethods__
        missing_methods = required_methods - abstract_methods
        extra_methods = abstract_methods - required_methods
        
        assert not missing_methods, f"Missing abstract methods: {missing_methods}"
        assert not extra_methods, f"Unexpected abstract methods: {extra_methods}"
    
    def test_provider_registration(self):
        """Test that providers are properly registered."""
        providers = llm_provider_registry.list_providers()
        assert len(providers) > 0, "No providers registered"
        
        # Check that expected providers are registered
        expected_providers = {"anthropic", "openai", "deepseek"}
        registered_providers = set(providers)
        
        # At least some of the expected providers should be registered
        assert registered_providers.intersection(expected_providers), \
            f"Expected at least one of {expected_providers}, got {registered_providers}"
    
    def test_provider_instantiation(self):
        """Test that providers can be instantiated with valid config."""
        providers = llm_provider_registry.list_providers()
        
        for provider_name in providers:
            # Create config appropriate for the provider
            if provider_name == "anthropic":
                config = LLMConfig(provider=ModelProvider.ANTHROPIC)
            elif provider_name == "openai":
                config = LLMConfig(provider=ModelProvider.OPENAI)
            elif provider_name == "deepseek":
                config = LLMConfig(provider=ModelProvider.DEEPSEEK)
            else:
                config = LLMConfig()
            
            # Should be able to create provider
            provider = llm_provider_registry.get_provider(provider_name, config)
            assert isinstance(provider, ILLMProvider), \
                f"Provider {provider_name} must implement ILLMProvider"
            
            # Test required methods exist
            assert hasattr(provider, 'complete')
            assert hasattr(provider, 'stream_response')
            assert hasattr(provider, 'get_cost_estimate')
            assert hasattr(provider, 'validate_config')
            assert hasattr(provider, 'model_identifier')
            
            # Test class methods exist
            provider_class = provider.__class__
            assert hasattr(provider_class, 'create')
            assert hasattr(provider_class, 'supported_models')
            assert hasattr(provider_class, 'get_provider_name')
    
    def test_provider_config_validation(self):
        """Test that providers validate their configuration properly."""
        providers = llm_provider_registry.list_providers()
        
        for provider_name in providers:
            # Create config appropriate for the provider
            if provider_name == "anthropic":
                config = LLMConfig(provider=ModelProvider.ANTHROPIC)
            elif provider_name == "openai":
                config = LLMConfig(provider=ModelProvider.OPENAI)
            elif provider_name == "deepseek":
                config = LLMConfig(provider=ModelProvider.DEEPSEEK)
            else:
                config = LLMConfig()
            
            provider = llm_provider_registry.get_provider(provider_name, config)
            
            # Valid config should pass validation
            assert provider.validate_config(config), \
                f"Provider {provider_name} should accept valid config"
            
            # Invalid config should raise ValueError
            invalid_config = LLMConfig(temperature=3.0)  # Invalid temperature
            with pytest.raises(ValueError):
                provider.validate_config(invalid_config)
    
    def test_provider_supported_models(self):
        """Test that providers return valid supported models."""
        providers = llm_provider_registry.list_providers()
        
        for provider_name in providers:
            provider_class = llm_provider_registry.get_provider_class(provider_name)
            models = provider_class.supported_models()
            
            assert isinstance(models, list), \
                f"Provider {provider_name} must return list of supported models"
            assert len(models) > 0, \
                f"Provider {provider_name} must support at least one model"
            
            for model in models:
                assert isinstance(model, str), \
                    f"Provider {provider_name} model names must be strings"
                assert len(model) > 0, \
                    f"Provider {provider_name} model names cannot be empty"
    
    def test_provider_cost_estimation(self):
        """Test that providers can estimate costs."""
        providers = llm_provider_registry.list_providers()
        test_prompt = "This is a test prompt for cost estimation."
        
        for provider_name in providers:
            # Create config appropriate for the provider
            if provider_name == "anthropic":
                config = LLMConfig(provider=ModelProvider.ANTHROPIC)
            elif provider_name == "openai":
                config = LLMConfig(provider=ModelProvider.OPENAI)
            elif provider_name == "deepseek":
                config = LLMConfig(provider=ModelProvider.DEEPSEEK)
            else:
                config = LLMConfig()
            
            provider = llm_provider_registry.get_provider(provider_name, config)
            cost = provider.get_cost_estimate(test_prompt)
            
            assert isinstance(cost, float), \
                f"Provider {provider_name} must return float cost estimate"
            assert cost >= 0.0, \
                f"Provider {provider_name} cost estimate must be non-negative"
    
    def test_provider_model_identifier(self):
        """Test that providers have valid model identifiers."""
        providers = llm_provider_registry.list_providers()
        
        for provider_name in providers:
            # Create config appropriate for the provider
            if provider_name == "anthropic":
                config = LLMConfig(provider=ModelProvider.ANTHROPIC)
            elif provider_name == "openai":
                config = LLMConfig(provider=ModelProvider.OPENAI)
            elif provider_name == "deepseek":
                config = LLMConfig(provider=ModelProvider.DEEPSEEK)
            else:
                config = LLMConfig()
            
            provider = llm_provider_registry.get_provider(provider_name, config)
            model_id = provider.model_identifier
            
            assert isinstance(model_id, str), \
                f"Provider {provider_name} must return string model identifier"
            assert len(model_id) > 0, \
                f"Provider {provider_name} model identifier cannot be empty"
    
    def test_provider_name_consistency(self):
        """Test that provider names are consistent."""
        providers = llm_provider_registry.list_providers()
        
        for provider_name in providers:
            provider_class = llm_provider_registry.get_provider_class(provider_name)
            class_provider_name = provider_class.get_provider_name()
            
            assert class_provider_name == provider_name, \
                f"Provider class {provider_class.__name__} name mismatch: " \
                f"expected {provider_name}, got {class_provider_name}" 