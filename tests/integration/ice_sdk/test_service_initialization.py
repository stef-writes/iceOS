"""Comprehensive service initialization tests.

These tests validate the core service initialization patterns that are fundamental
to iceOS architecture. They ensure services are properly registered, dependencies
are resolved correctly, and initialization order is maintained.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from ice_sdk.services.locator import ServiceLocator
from ice_sdk.services.initialization import initialize_services
from ice_sdk.context.manager import GraphContextManager  
from ice_sdk.tools.service import ToolService
from ice_sdk.providers.llm_service import LLMService


class TestServiceLocatorCore:
    """Test the fundamental ServiceLocator pattern."""
    
    def setup_method(self):
        """Clear services before each test."""
        ServiceLocator.clear()
    
    def teardown_method(self):
        """Clear services after each test."""
        ServiceLocator.clear()
    
    def test_service_registration_and_retrieval(self):
        """Test basic service registration and retrieval."""
        mock_service = Mock()
        
        # Registration should work
        ServiceLocator.register("test_service", mock_service)
        
        # Retrieval should return the same instance
        retrieved = ServiceLocator.get("test_service")
        assert retrieved is mock_service
    
    def test_service_not_found_returns_none(self):
        """Test that missing services return None, not raise exceptions."""
        result = ServiceLocator.get("nonexistent_service")
        assert result is None
    
    def test_service_replacement_allowed(self):
        """Test that services can be replaced (for testing/re-initialization)."""
        service1 = Mock()
        service2 = Mock()
        
        ServiceLocator.register("replaceable", service1)
        ServiceLocator.register("replaceable", service2)
        
        retrieved = ServiceLocator.get("replaceable")
        assert retrieved is service2  # Should be the latest
        assert retrieved is not service1
    
    def test_thread_safety_basic(self):
        """Test basic thread safety of ServiceLocator.""" 
        import threading
        import time
        
        results = []
        
        def register_service(name, value):
            ServiceLocator.register(name, value)
            time.sleep(0.01)  # Simulate some work
            results.append(ServiceLocator.get(name))
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_service, args=(f"service_{i}", i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All registrations should have succeeded
        assert len(results) == 10
        for i in range(10):
            assert ServiceLocator.get(f"service_{i}") == i


class TestServiceInitializationOrder:
    """Test that service initialization order is correct and dependencies work."""
    
    def setup_method(self):
        ServiceLocator.clear()
    
    def teardown_method(self):
        ServiceLocator.clear()
    
    def test_tool_service_available_before_context_manager(self):
        """Test that ToolService is available when GraphContextManager is created."""
        # Simulate the correct initialization order from main.py
        tool_service = ToolService()
        ServiceLocator.register("tool_service", tool_service)
        
        # Context manager should find the registered tool service
        ctx_manager = GraphContextManager(project_root=Path.cwd())
        
        # The context manager should have the tool service
        assert ctx_manager.tool_service is not None
        assert ctx_manager.tool_service is tool_service
    
    def test_context_manager_creates_tool_service_if_missing(self):
        """Test that GraphContextManager creates ToolService if none registered."""
        # Don't register any tool service
        
        # Context manager should create its own
        ctx_manager = GraphContextManager(project_root=Path.cwd())
        
        # Should have created and registered a tool service
        assert ctx_manager.tool_service is not None
        assert isinstance(ctx_manager.tool_service, ToolService)
        
        # Should have registered it with ServiceLocator
        registered_service = ServiceLocator.get("tool_service")
        assert registered_service is ctx_manager.tool_service
    
    def test_initialize_services_function(self):
        """Test the initialize_services() function sets up expected services."""
        # Call the main initialization function
        initialize_services()
        
        # Should register builder_service and llm_service
        builder_service = ServiceLocator.get("builder_service")
        llm_service = ServiceLocator.get("llm_service")
        
        assert builder_service is not None
        assert llm_service is not None


class TestContextManagerIntegration:
    """Test GraphContextManager integration with services."""
    
    def setup_method(self):
        ServiceLocator.clear()
    
    def teardown_method(self):
        ServiceLocator.clear()
    
    def test_tool_registration_with_service(self):
        """Test that tool registration works end-to-end."""
        from ice_sdk.tools.system.csv_reader_tool import CSVReaderTool
        
        # Set up services properly
        tool_service = ToolService()
        ServiceLocator.register("tool_service", tool_service)
        
        ctx_manager = GraphContextManager(project_root=Path.cwd())
        
        # Should be able to register a tool without errors
        tool = CSVReaderTool()
        ctx_manager.register_tool(tool)
        
        # Tool should be registered in both places
        assert ctx_manager.get_tool("csv_reader") is tool
        # Tool class should be registered with ToolService
        assert "csv_reader" in tool_service.available_tools()
    
    def test_tool_registration_handles_duplicates(self):
        """Test that duplicate tool registration is handled gracefully."""
        from ice_sdk.tools.system.csv_reader_tool import CSVReaderTool
        
        tool_service = ToolService()
        ServiceLocator.register("tool_service", tool_service)
        
        ctx_manager = GraphContextManager(project_root=Path.cwd())
        
        # CSVReaderTool is already registered globally at import time
        # So the tool_service already knows about it
        assert "csv_reader" in tool_service.available_tools()
        
        # Create tool instances
        tool1 = CSVReaderTool()
        tool2 = CSVReaderTool()
        
        # First registration in context manager should work
        ctx_manager.register_tool(tool1)
        assert ctx_manager.get_tool("csv_reader") is tool1
        
        # Second registration in context manager should raise error
        with pytest.raises(ValueError, match="Tool 'csv_reader' already registered"):
            ctx_manager.register_tool(tool2)
        
        # Verify the first tool is still registered
        assert ctx_manager.get_tool("csv_reader") is tool1


class TestServiceInitializationErrorHandling:
    """Test error handling in service initialization."""
    
    def setup_method(self):
        ServiceLocator.clear()
    
    def teardown_method(self):
        ServiceLocator.clear()
    
    def test_missing_orchestrator_handled_gracefully(self):
        """Test that missing orchestrator doesn't break SDK initialization."""
        with patch('ice_orchestrator.initialize_orchestrator') as mock_init:
            mock_init.side_effect = ImportError("No orchestrator")
            
            # Should not raise an exception
            initialize_services()
            
            # Should still register SDK services
            assert ServiceLocator.get("builder_service") is not None
    
    def test_partial_service_failure_isolation(self):
        """Test that failure in one service doesn't break others."""
        with patch('ice_sdk.services.builder_service.BuilderService') as mock_builder:
            mock_builder.side_effect = ImportError("Builder broken")
            
            # Should not raise exception
            initialize_services()
            
            # LLM service should still be registered
            assert ServiceLocator.get("llm_service") is not None
            # Builder service should be None
            assert ServiceLocator.get("builder_service") is None


class TestRealWorldIntegrationPattern:
    """Test the actual patterns used in main.py and real applications."""
    
    def setup_method(self):
        ServiceLocator.clear()
    
    def teardown_method(self):
        ServiceLocator.clear()
    
    def test_main_py_initialization_pattern(self):
        """Test the exact pattern used in main.py works correctly."""
        from ice_sdk.services.initialization import initialize_services
        
        # Simulate main.py lifespan function
        initialize_services()
        
        project_root = Path.cwd()
        tool_service = ToolService()
        
        # Register tool service BEFORE creating context manager
        ServiceLocator.register("tool_service", tool_service)
        ServiceLocator.register("llm_service", LLMService())
        
        # Now create context manager (it will find the registered tool_service)
        ctx_manager = GraphContextManager(project_root=project_root)
        ServiceLocator.register("context_manager", ctx_manager)
        
        # Validate the setup
        assert ctx_manager.tool_service is tool_service
        assert ServiceLocator.get("context_manager") is ctx_manager
        assert ServiceLocator.get("tool_service") is tool_service
        assert isinstance(ServiceLocator.get("llm_service"), LLMService)
    
    def test_workflow_service_tool_registration(self):
        """Test that WorkflowService can register tools with context manager."""
        from ice_sdk.tools.system.csv_reader_tool import CSVReaderTool
        
        # Set up the full service stack
        initialize_services()
        
        tool_service = ToolService()
        ServiceLocator.register("tool_service", tool_service)
        
        ctx_manager = GraphContextManager(project_root=Path.cwd())
        ServiceLocator.register("context_manager", ctx_manager)
        
        # Simulate what WorkflowService does
        csv_tool = CSVReaderTool()
        ctx_manager.register_tool(csv_tool)
        
        # Should work without the AttributeError we were seeing
        assert ctx_manager.get_tool("csv_reader") is csv_tool


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 