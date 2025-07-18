import pytest
from decimal import Decimal
from ice_sdk.providers.costs import CostTracker


class TestCostTracker:
    """Test cost tracking functionality"""
    
    def test_initialization(self):
        """Test CostTracker initializes with zero costs"""
        tracker = CostTracker()
        assert tracker._total_cost == Decimal("0")
        assert tracker._budget is None
        assert tracker._start_time is None
    
    def test_reset(self):
        """Test reset functionality"""
        tracker = CostTracker()
        tracker._total_cost = Decimal("10.50")
        tracker._budget = Decimal("5.00")
        tracker._start_time = 1234567890.0
        
        tracker.reset()
        
        assert tracker._total_cost == Decimal("0")
        assert tracker._budget is None
        assert tracker._start_time is None
    
    def test_set_budget(self):
        """Test budget setting"""
        tracker = CostTracker()
        tracker.set_budget(5.50)
        assert tracker._budget == Decimal("5.50")
    
    def test_add_cost_within_budget(self):
        """Test adding cost within budget limit"""
        tracker = CostTracker()
        tracker.set_budget(10.00)
        
        # Add costs within budget
        tracker.add_cost(Decimal("3.50"))
        tracker.add_cost(Decimal("2.00"))
        
        assert tracker._total_cost == Decimal("5.50")
    
    def test_add_cost_exceeds_budget(self):
        """Test that exceeding budget raises exception"""
        tracker = CostTracker()
        tracker.set_budget(5.00)
        
        # Add cost within budget
        tracker.add_cost(Decimal("3.00"))
        
        # Try to exceed budget
        with pytest.raises(RuntimeError, match="Budget exceeded"):
            tracker.add_cost(Decimal("3.00"))
    
    def test_time_tracking(self):
        """Test execution time tracking"""
        tracker = CostTracker()
        
        # Start tracking
        tracker.start_tracking()
        assert tracker._start_time is not None
        
        # Stop tracking
        tracker.stop_tracking()
        assert tracker._execution_time is not None
        assert tracker._execution_time >= 0
    
    def test_get_costs(self):
        """Test cost summary retrieval"""
        tracker = CostTracker()
        tracker.set_budget(10.00)
        tracker.add_cost(Decimal("3.50"))
        
        costs = tracker.get_costs()
        
        assert costs["total"] == 3.50
        assert costs["budget"] == 10.00
    
    def test_get_costs_no_budget(self):
        """Test cost summary without budget"""
        tracker = CostTracker()
        tracker.add_cost(Decimal("2.75"))
        
        costs = tracker.get_costs()
        
        assert costs["total"] == 2.75
        assert costs["budget"] is None
    
    def test_get_execution_time(self):
        """Test execution time retrieval"""
        tracker = CostTracker()
        
        # No tracking started
        assert tracker.get_execution_time() is None
        
        # Start and stop tracking
        tracker.start_tracking()
        tracker.stop_tracking()
        
        execution_time = tracker.get_execution_time()
        assert execution_time is not None
        assert execution_time >= 0 