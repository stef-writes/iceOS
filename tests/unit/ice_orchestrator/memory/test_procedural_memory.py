"""Comprehensive unit tests for ProceduralMemory."""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from ice_orchestrator.memory.procedural import ProceduralMemory
from ice_orchestrator.memory import MemoryConfig


class TestProceduralMemory:
    """Test suite for ProceduralMemory implementation."""
    
    @pytest_asyncio.fixture
    async def memory(self):
        """Create ProceduralMemory instance."""
        config = MemoryConfig(backend="memory")
        memory = ProceduralMemory(config)
        await memory.initialize()
        yield memory
        await memory.clear()
    
    @pytest.mark.asyncio
    async def test_initialization_with_defaults(self, memory):
        """Test that default procedures are loaded on initialization."""
        # Should have default procedures loaded
        procedures = await memory.list_keys()
        assert len(procedures) > 0
        
        # Check specific defaults exist
        negotiation = await memory.retrieve("negotiation_standard")
        assert negotiation is not None
        assert negotiation.content["name"] == "Standard Negotiation"
        assert "steps" in negotiation.content
        
        response = await memory.retrieve("response_availability_positive")
        assert response is not None
        assert "template" in response.content
        
        closing = await memory.retrieve("closing_sequence_standard")
        assert closing is not None
        assert "steps" in closing.content
    
    @pytest.mark.asyncio
    async def test_store_procedure(self, memory):
        """Test storing new procedures."""
        # Store a simple response template
        await memory.store(
            key="greeting_template",
            content={
                "name": "Friendly Greeting",
                "template": "Hello {customer_name}! How can I help you today?",
                "variables": ["customer_name"],
                "sentiment": "positive"
            },
            metadata={
                "category": "response_template",
                "contexts": ["initial_contact", "greeting"],
                "success_rate": 0.9
            }
        )
        
        # Retrieve and verify
        greeting = await memory.retrieve("greeting_template")
        assert greeting is not None
        assert greeting.content["name"] == "Friendly Greeting"
        assert greeting.metadata["category"] == "response_template"
        assert "initial_contact" in greeting.metadata["contexts"]
    
    @pytest.mark.asyncio
    async def test_validation(self, memory):
        """Test procedure validation."""
        # Missing name should raise error
        with pytest.raises(ValueError, match="must have a name"):
            await memory.store(
                key="invalid_1",
                content={"template": "No name here"}
            )
        
        # Non-dict content should raise error
        with pytest.raises(ValueError, match="must be a dictionary"):
            await memory.store(
                key="invalid_2",
                content="Not a dict"
            )
    
    @pytest.mark.asyncio
    async def test_search_procedures(self, memory):
        """Test searching procedures."""
        # Store various procedures
        procedures = [
            ("price_negotiation", {
                "name": "Price Negotiation",
                "steps": ["acknowledge", "evaluate", "counter"],
                "category": "negotiation"
            }),
            ("availability_response", {
                "name": "Availability Response",
                "template": "Yes, it's available!",
                "category": "response"
            }),
            ("shipping_negotiation", {
                "name": "Shipping Negotiation",
                "description": "Handle shipping cost discussions",
                "category": "negotiation"
            })
        ]
        
        for key, content in procedures:
            await memory.store(
                key=key,
                content=content,
                metadata={"category": content.get("category", "general")}
            )
        
        # Search for negotiation procedures
        results = await memory.search("negotiation")
        assert len(results) >= 2  # Plus defaults
        
        # Search with category filter
        results = await memory.search(
            "", 
            filters={"category": "negotiation"}
        )
        negotiation_keys = [r.key for r in results]
        assert "price_negotiation" in negotiation_keys
        assert "shipping_negotiation" in negotiation_keys
    
    @pytest.mark.asyncio
    async def test_find_applicable_procedures(self, memory):
        """Test finding procedures applicable to context."""
        # Store context-specific procedures
        await memory.store(
            key="high_value_negotiation",
            content={
                "name": "High Value Item Negotiation",
                "steps": ["emphasize_quality", "small_discount"],
                "applicable_when": {
                    "item_value": [500, 10000],
                    "buyer_engagement": "high"
                }
            },
            metadata={
                "category": "negotiation",
                "contexts": ["price_inquiry", "offer_received"]
            }
        )
        
        await memory.store(
            key="low_value_quick_sale",
            content={
                "name": "Quick Sale for Low Value",
                "steps": ["accept_reasonable_offer"],
                "applicable_when": {
                    "item_value": [0, 100],
                    "time_on_market": [7, 999]
                }
            },
            metadata={
                "category": "negotiation",
                "contexts": ["price_inquiry"]
            }
        )
        
        # Test with high value context
        high_value_context = {
            "type": "price_inquiry",
            "item_value": 750,
            "buyer_engagement": "high"
        }
        
        applicable = await memory.find_applicable_procedures(
            high_value_context,
            category="negotiation"
        )
        
        # Should find high value negotiation
        keys = [p.key for p in applicable]
        assert "high_value_negotiation" in keys
        assert "low_value_quick_sale" not in keys  # Value too high
        
        # Test with low value context
        low_value_context = {
            "type": "price_inquiry",
            "item_value": 50,
            "time_on_market": 14
        }
        
        applicable = await memory.find_applicable_procedures(
            low_value_context,
            category="negotiation"
        )
        
        keys = [p.key for p in applicable]
        assert "low_value_quick_sale" in keys
        assert "high_value_negotiation" not in keys  # Value too low
    
    @pytest.mark.asyncio
    async def test_prerequisites(self, memory):
        """Test procedures with prerequisites."""
        await memory.store(
            key="closing_with_payment",
            content={
                "name": "Close Sale with Payment",
                "steps": ["confirm_payment_method", "process_payment", "confirm_sale"]
            },
            metadata={
                "category": "closing",
                "prerequisites": ["payment_method_verified", "price_agreed"],
                "contexts": ["closing_sale"]
            }
        )
        
        # Context without prerequisites
        context_incomplete = {
            "type": "closing_sale",
            "price_agreed": True
            # Missing payment_method_verified
        }
        
        applicable = await memory.find_applicable_procedures(
            context_incomplete,
            category="closing"
        )
        
        # Should not find the procedure
        keys = [p.key for p in applicable]
        assert "closing_with_payment" not in keys
        
        # Context with all prerequisites
        context_complete = {
            "type": "closing_sale",
            "price_agreed": True,
            "payment_method_verified": True
        }
        
        applicable = await memory.find_applicable_procedures(
            context_complete,
            category="closing"
        )
        
        keys = [p.key for p in applicable]
        assert "closing_with_payment" in keys
    
    @pytest.mark.asyncio
    async def test_record_execution(self, memory):
        """Test recording procedure execution and outcomes."""
        # Get a default procedure
        procedure = await memory.retrieve("negotiation_standard")
        assert procedure is not None
        
        # Record successful execution
        await memory.record_execution(
            "negotiation_standard",
            {
                "success_score": 0.9,
                "result": "sale_completed",
                "final_price": 450
            }
        )
        
        # Check updated metrics
        updated = await memory.retrieve("negotiation_standard")
        assert updated.metadata["usage_count"] == 1
        assert updated.metadata["last_used"] is not None
        
        # Record multiple executions with varying success
        for score in [0.8, 0.7, 0.9, 0.95]:
            await memory.record_execution(
                "negotiation_standard",
                {"success_score": score}
            )
        
        # Check updated success rate
        final = await memory.retrieve("negotiation_standard")
        assert final.metadata["usage_count"] == 5
        # Success rate should be weighted average favoring recent
        assert 0.7 < final.metadata["success_rate"] < 0.95
    
    @pytest.mark.asyncio
    async def test_learned_adjustments(self, memory):
        """Test applying learned adjustments to procedures."""
        # Create a procedure to adjust
        await memory.store(
            key="adjustable_procedure",
            content={
                "name": "Adjustable Response",
                "steps": [
                    {"action": "greet", "template": "Hello!"},
                    {"action": "offer", "template": "Would you like this?"}
                ]
            }
        )
        
        # Record execution with learned adjustments
        await memory.record_execution(
            "adjustable_procedure",
            {
                "success_score": 0.95,
                "learned_adjustments": {
                    "template_improvements": {
                        "0": "Hi there! Welcome!",
                        "1": "I think you'll love this - interested?"
                    },
                    "condition_adjustments": {
                        "time_of_day": "morning"
                    }
                }
            }
        )
        
        # Check adjustments were applied
        adjusted = await memory.retrieve("adjustable_procedure")
        assert adjusted.content["steps"][0]["template"] == "Hi there! Welcome!"
        assert adjusted.content["steps"][1]["template"] == "I think you'll love this - interested?"
        assert adjusted.content["applicable_when"]["time_of_day"] == "morning"
        assert adjusted.metadata["last_modified"] is not None
        assert adjusted.metadata["modification_count"] == 1
    
    @pytest.mark.asyncio
    async def test_get_best_procedures(self, memory):
        """Test retrieving best performing procedures."""
        # Create procedures with different performance
        procedures = [
            ("high_performer", 0.9, 10),
            ("medium_performer", 0.7, 15),
            ("low_performer", 0.4, 20),
            ("untested", 0.5, 2)
        ]
        
        for key, success_rate, usage in procedures:
            await memory.store(
                key=key,
                content={"name": f"Procedure {key}"},
                metadata={
                    "category": "test_category",
                    "success_rate": success_rate,
                    "usage_count": usage
                }
            )
        
        # Get best procedures
        best = await memory.get_best_procedures(
            "test_category",
            min_success_rate=0.6
        )
        
        # Should get high and medium performers (enough usage)
        keys = [p.key for p in best]
        assert "high_performer" in keys
        assert "medium_performer" in keys
        assert "low_performer" not in keys  # Below threshold
        assert "untested" not in keys  # Not enough usage
    
    @pytest.mark.asyncio
    async def test_category_indexing(self, memory):
        """Test category-based indexing."""
        # Store procedures in categories
        categories = ["response", "negotiation", "closing"]
        
        for i, category in enumerate(categories):
            for j in range(3):
                await memory.store(
                    key=f"{category}_{j}",
                    content={"name": f"{category} procedure {j}"},
                    metadata={"category": category}
                )
        
        # Check category index
        for category in categories:
            procedures = await memory.search(
                "",
                filters={"category": category}
            )
            assert len(procedures) >= 3
    
    @pytest.mark.asyncio
    async def test_context_indexing(self, memory):
        """Test context-based indexing."""
        # Store procedures with contexts
        await memory.store(
            key="multi_context_proc",
            content={"name": "Multi Context Procedure"},
            metadata={
                "contexts": ["greeting", "initial_inquiry", "availability_check"]
            }
        )
        
        # Should be findable by any context
        for context in ["greeting", "initial_inquiry", "availability_check"]:
            context_obj = {"type": context}
            applicable = await memory.find_applicable_procedures(context_obj)
            keys = [p.key for p in applicable]
            assert "multi_context_proc" in keys
    
    @pytest.mark.asyncio
    async def test_create_composite_procedure(self, memory):
        """Test creating composite procedures."""
        # Create component procedures
        await memory.store(
            key="greeting_component",
            content={
                "name": "Greeting",
                "template": "Hello {name}!"
            },
            metadata={"contexts": ["greeting"]}
        )
        
        await memory.store(
            key="offer_component",
            content={
                "name": "Make Offer",
                "steps": [
                    {"action": "present_item"},
                    {"action": "state_price"}
                ]
            },
            metadata={"contexts": ["sales_pitch"]}
        )
        
        await memory.store(
            key="urgency_component",
            content={
                "name": "Create Urgency",
                "template": "Limited time offer!"
            },
            metadata={
                "contexts": ["closing"],
                "prerequisites": ["price_stated"]
            }
        )
        
        # Create composite
        success = await memory.create_composite_procedure(
            ["greeting_component", "offer_component", "urgency_component"],
            "full_sales_sequence",
            "Complete Sales Sequence"
        )
        
        assert success is True
        
        # Check composite
        composite = await memory.retrieve("full_sales_sequence")
        assert composite is not None
        assert composite.content["type"] == "composite"
        assert len(composite.content["steps"]) == 4  # 1 + 2 + 1
        assert composite.metadata["category"] == "composite"
        
        # Should have all contexts
        contexts = composite.metadata["contexts"]
        assert "greeting" in contexts
        assert "sales_pitch" in contexts
        assert "closing" in contexts
        
        # Should have prerequisites from components
        assert "price_stated" in composite.metadata["prerequisites"]
    
    @pytest.mark.asyncio
    async def test_export_successful_procedures(self, memory):
        """Test exporting successful procedures."""
        # Create mix of procedures
        await memory.store(
            key="export_success",
            content={"name": "Successful Procedure"},
            metadata={
                "category": "test",
                "success_rate": 0.85,
                "usage_count": 20
            }
        )
        
        await memory.store(
            key="export_fail",
            content={"name": "Failed Procedure"},
            metadata={
                "category": "test",
                "success_rate": 0.3,
                "usage_count": 15
            }
        )
        
        # Export successful ones
        export = await memory.export_successful_procedures(
            min_success_rate=0.7,
            min_usage=10
        )
        
        assert "procedures" in export
        assert "export_success" in export["procedures"]
        assert "export_fail" not in export["procedures"]
        
        # Check export metadata
        assert export["criteria"]["min_success_rate"] == 0.7
        assert export["criteria"]["min_usage"] == 10
        assert "export_date" in export
    
    @pytest.mark.asyncio
    async def test_delete_operations(self, memory):
        """Test deletion functionality."""
        # Store procedure with indexes
        await memory.store(
            key="delete_test",
            content={"name": "To Delete"},
            metadata={
                "category": "test_cat",
                "contexts": ["test_ctx1", "test_ctx2"]
            }
        )
        
        # Verify in indexes
        assert "delete_test" in memory._category_index["test_cat"]
        assert "delete_test" in memory._context_index["test_ctx1"]
        
        # Delete
        deleted = await memory.delete("delete_test")
        assert deleted is True
        
        # Verify removed from indexes
        assert "delete_test" not in memory._category_index["test_cat"]
        assert "delete_test" not in memory._context_index["test_ctx1"]
        assert await memory.retrieve("delete_test") is None
        
        # Delete non-existent
        assert await memory.delete("nonexistent") is False
    
    @pytest.mark.asyncio
    async def test_clear_operations(self, memory):
        """Test clear functionality."""
        # Store procedures with patterns
        for i in range(3):
            await memory.store(
                key=f"temp_proc_{i}",
                content={"name": f"Temp {i}"}
            )
            await memory.store(
                key=f"keep_proc_{i}",
                content={"name": f"Keep {i}"}
            )
        
        # Clear by pattern
        cleared = await memory.clear("temp_proc_")
        assert cleared == 3
        
        # Verify cleared
        assert await memory.retrieve("temp_proc_0") is None
        assert await memory.retrieve("keep_proc_0") is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, memory):
        """Test concurrent access patterns."""
        # Concurrent stores
        tasks = []
        for i in range(10):
            task = memory.store(
                key=f"concurrent_{i}",
                content={"name": f"Concurrent {i}"},
                metadata={"index": i}
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all stored
        for i in range(10):
            proc = await memory.retrieve(f"concurrent_{i}")
            assert proc is not None
            assert proc.metadata["index"] == i
        
        # Concurrent execution recording
        exec_tasks = []
        for i in range(10):
            task = memory.record_execution(
                f"concurrent_{i}",
                {"success_score": 0.5 + i * 0.05}
            )
            exec_tasks.append(task)
        
        await asyncio.gather(*exec_tasks)
        
        # Verify all recorded
        for i in range(10):
            proc = await memory.retrieve(f"concurrent_{i}")
            assert proc.metadata["usage_count"] == 1
    
    @pytest.mark.asyncio
    async def test_success_rate_calculation(self, memory):
        """Test weighted success rate calculation."""
        await memory.store(
            key="rate_test",
            content={"name": "Rate Test"},
            metadata={"success_rate": 0.5}
        )
        
        # Record executions with different scores
        scores = [0.3, 0.4, 0.6, 0.8, 0.9]  # Average = 0.6
        
        for score in scores:
            await memory.record_execution(
                "rate_test",
                {"success_score": score}
            )
        
        # Check weighted rate (recent scores weighted more)
        proc = await memory.retrieve("rate_test")
        success_rate = proc.metadata["success_rate"]
        
        # Should be higher than simple average due to weighting
        assert success_rate > 0.6
        assert success_rate < 0.9  # But not as high as best score
    
    @pytest.mark.asyncio
    async def test_metadata_enrichment(self, memory):
        """Test metadata enrichment on storage."""
        # Store with minimal metadata
        await memory.store(
            key="enrichment_test",
            content={"name": "Test"},
            metadata={"custom": "value"}
        )
        
        # Retrieve and check defaults
        proc = await memory.retrieve("enrichment_test")
        
        assert proc.metadata["category"] == "general"
        assert proc.metadata["success_rate"] == 0.5
        assert proc.metadata["usage_count"] == 0
        assert proc.metadata["last_used"] is None
        assert isinstance(proc.metadata["contexts"], list)
        assert isinstance(proc.metadata["prerequisites"], list)
        assert isinstance(proc.metadata["outcomes"], list)
        
        # Custom field preserved
        assert proc.metadata["custom"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 