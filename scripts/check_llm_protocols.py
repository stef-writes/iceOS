#!/usr/bin/env python3
"""CI script to validate LLM provider protocol compliance.

This script ensures that all LLM providers properly implement the ILLMProvider
protocol and can be instantiated without errors.
"""
from __future__ import annotations

import inspect
import sys
from typing import List, Type

from ice_core.models.llm import LLMConfig
from ice_core.protocols.llm import ILLMProvider, llm_provider_registry


def validate_provider_class(provider_class: Type[ILLMProvider]) -> List[str]:
    """Validate a provider class for protocol compliance.
    
    Args:
        provider_class: Provider class to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check that it's a subclass of ILLMProvider
    if not issubclass(provider_class, ILLMProvider):
        errors.append(f"{provider_class.__name__} must inherit from ILLMProvider")
        return errors
    
    # Check that it's not abstract
    if inspect.isabstract(provider_class):
        errors.append(f"{provider_class.__name__} is abstract - all methods must be implemented")
        return errors
    
    # Check required class methods
    required_class_methods = ['create', 'supported_models', 'get_provider_name']
    for method_name in required_class_methods:
        if not hasattr(provider_class, method_name):
            errors.append(f"{provider_class.__name__} missing required class method: {method_name}")
        elif not inspect.ismethod(getattr(provider_class, method_name)):
            errors.append(f"{provider_class.__name__}.{method_name} must be a class method")
    
    # Check required instance methods
    required_instance_methods = ['stream_response', 'complete', 'get_cost_estimate', 'validate_config']
    for method_name in required_instance_methods:
        if not hasattr(provider_class, method_name):
            errors.append(f"{provider_class.__name__} missing required instance method: {method_name}")
    
    # Check required properties
    required_properties = ['model_identifier']
    for prop_name in required_properties:
        if not hasattr(provider_class, prop_name):
            errors.append(f"{provider_class.__name__} missing required property: {prop_name}")
    
    return errors


def validate_provider_instance(provider_class: Type[ILLMProvider]) -> List[str]:
    """Validate that a provider can be instantiated and used.
    
    Args:
        provider_class: Provider class to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    try:
        # Create a default config
        config = LLMConfig()
        
        # Try to create provider instance
        provider = provider_class.create(config)
        
        # Check that it's an instance of ILLMProvider
        if not isinstance(provider, ILLMProvider):
            errors.append(f"{provider_class.__name__}.create() must return ILLMProvider instance")
            return errors
        
        # Test required methods
        try:
            # Test model_identifier property
            model_id = provider.model_identifier
            if not isinstance(model_id, str) or len(model_id) == 0:
                errors.append(f"{provider_class.__name__}.model_identifier must return non-empty string")
        except Exception as e:
            errors.append(f"{provider_class.__name__}.model_identifier failed: {e}")
        
        try:
            # Test get_cost_estimate method
            cost = provider.get_cost_estimate("test prompt")
            if not isinstance(cost, (int, float)) or cost < 0:
                errors.append(f"{provider_class.__name__}.get_cost_estimate must return non-negative number")
        except Exception as e:
            errors.append(f"{provider_class.__name__}.get_cost_estimate failed: {e}")
        
        try:
            # Test validate_config method
            valid = provider.validate_config(config)
            if not isinstance(valid, bool):
                errors.append(f"{provider_class.__name__}.validate_config must return boolean")
        except Exception as e:
            errors.append(f"{provider_class.__name__}.validate_config failed: {e}")
        
        # Test class methods
        try:
            models = provider_class.supported_models()
            if not isinstance(models, list) or len(models) == 0:
                errors.append(f"{provider_class.__name__}.supported_models must return non-empty list")
        except Exception as e:
            errors.append(f"{provider_class.__name__}.supported_models failed: {e}")
        
        try:
            name = provider_class.get_provider_name()
            if not isinstance(name, str) or len(name) == 0:
                errors.append(f"{provider_class.__name__}.get_provider_name must return non-empty string")
        except Exception as e:
            errors.append(f"{provider_class.__name__}.get_provider_name failed: {e}")
        
    except Exception as e:
        errors.append(f"Failed to instantiate {provider_class.__name__}: {e}")
    
    return errors


def main() -> int:
    """Main validation function.
    
    Returns:
        0 if all providers are valid, 1 if any errors found
    """
    print("Validating LLM provider protocol compliance...")
    
    all_errors = []
    
    # Get all registered providers
    providers = llm_provider_registry.list_providers()
    print(f"Found {len(providers)} registered providers: {', '.join(providers)}")
    
    for provider_name in providers:
        print(f"\nValidating provider: {provider_name}")
        
        try:
            provider_class = llm_provider_registry.get_provider_class(provider_name)
            
            # Validate class structure
            class_errors = validate_provider_class(provider_class)
            if class_errors:
                all_errors.extend([f"{provider_name}: {error}" for error in class_errors])
                continue
            
            # Validate instance creation and usage
            instance_errors = validate_provider_instance(provider_class)
            if instance_errors:
                all_errors.extend([f"{provider_name}: {error}" for error in instance_errors])
            else:
                print(f"✓ {provider_name} passed validation")
                
        except Exception as e:
            all_errors.append(f"{provider_name}: Failed to validate - {e}")
    
    # Report results
    if all_errors:
        print(f"\n❌ Found {len(all_errors)} validation errors:")
        for error in all_errors:
            print(f"  - {error}")
        return 1
    else:
        print(f"\n✅ All {len(providers)} providers passed validation")
        return 0


if __name__ == "__main__":
    sys.exit(main()) 