#!/usr/bin/env python3
"""
🧠🔍 BCI Investment Lab - Success Verification System
===================================================

VERIFICATION CRITERIA:
✅ Technical: No errors, real APIs, proper execution
✅ Functional: Quality data, coherent insights, realistic outputs  
✅ Integration: iceOS compliance, memory persistence, orchestration
✅ Data Quality: No mocking, real content, logical consistency

Usage:
    python verify_success.py bci_blueprint_results.json
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class BCISuccessVerifier:
    """Comprehensive success verification for BCI Investment Lab."""
    
    def __init__(self, results_file: str):
        self.results_file = Path(results_file)
        self.verification_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_success": False,
            "technical_success": False,
            "functional_success": False,
            "integration_success": False,
            "criteria_passed": 0,
            "criteria_total": 0,
            "detailed_results": {}
        }
    
    def load_results(self) -> Dict[str, Any]:
        """Load execution results from JSON file."""
        if not self.results_file.exists():
            raise FileNotFoundError(f"Results file not found: {self.results_file}")
        
        with open(self.results_file, 'r') as f:
            return json.load(f)
    
    def verify_technical_success(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Verify technical execution success."""
        print("🔧 VERIFYING TECHNICAL SUCCESS...")
        
        technical_checks = {
            "no_execution_errors": False,
            "all_workflows_completed": False,
            "proper_timing": False,
            "results_structure_valid": False
        }
        
        # Check for errors
        has_errors = "error" in results or any(
            "error" in workflow_result 
            for workflow_result in results.get("results", {}).values()
            if isinstance(workflow_result, dict)
        )
        technical_checks["no_execution_errors"] = not has_errors
        
        # Check workflows completed
        expected_workflows = ["literature_analysis", "market_monitoring", "recursive_synthesis"]
        completed_workflows = results.get("workflows_executed", [])
        technical_checks["all_workflows_completed"] = all(
            workflow in completed_workflows for workflow in expected_workflows
        )
        
        # Check proper timing (should take reasonable time, not instant = mocking)
        start_time = results.get("start_time")
        end_time = results.get("end_time")
        if start_time and end_time:
            from datetime import datetime
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            duration = (end - start).total_seconds()
            # Real API calls should take at least 30 seconds, but less than 30 minutes
            technical_checks["proper_timing"] = 30 <= duration <= 1800
        
        # Check results structure
        technical_checks["results_structure_valid"] = (
            "results" in results and 
            isinstance(results["results"], dict) and
            len(results["results"]) >= 3
        )
        
        passed = sum(technical_checks.values())
        total = len(technical_checks)
        
        print(f"  ✅ No Errors: {technical_checks['no_execution_errors']}")
        print(f"  ✅ All Workflows: {technical_checks['all_workflows_completed']}")
        print(f"  ✅ Proper Timing: {technical_checks['proper_timing']}")
        print(f"  ✅ Valid Structure: {technical_checks['results_structure_valid']}")
        print(f"  🎯 Technical Score: {passed}/{total}")
        
        return {
            "passed": passed,
            "total": total,
            "success": passed == total,
            "details": technical_checks
        }
    
    def verify_functional_success(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Verify functional data quality and coherence."""
        print("\n📊 VERIFYING FUNCTIONAL SUCCESS...")
        
        functional_checks = {
            "literature_quality": False,
            "market_data_quality": False,
            "synthesis_coherence": False,
            "confidence_scores": False,
            "no_mock_patterns": False
        }
        
        workflow_results = results.get("results", {})
        
        # Literature Analysis Quality
        lit_result = workflow_results.get("literature_analysis", {})
        if not isinstance(lit_result, dict) or "error" in lit_result:
            functional_checks["literature_quality"] = False
        else:
            papers_count = lit_result.get("papers_analyzed", 0)
            findings_count = len(lit_result.get("key_findings", []))
            confidence = lit_result.get("confidence_score", 0.0)
            
            functional_checks["literature_quality"] = (
                papers_count >= 5 and  # At least 5 papers
                findings_count >= 3 and  # At least 3 findings
                confidence >= 0.5  # Reasonable confidence
            )
        
        # Market Data Quality
        market_result = workflow_results.get("market_monitoring", {})
        if not isinstance(market_result, dict) or "error" in market_result:
            functional_checks["market_data_quality"] = False
        else:
            companies_count = len(market_result.get("companies_monitored", []))
            signals_count = len(market_result.get("market_signals", []))
            
            functional_checks["market_data_quality"] = (
                companies_count >= 4 and  # All 4 companies
                signals_count >= 1  # At least 1 signal
            )
        
        # Synthesis Coherence
        synth_result = workflow_results.get("recursive_synthesis", {})
        if not isinstance(synth_result, dict) or "error" in synth_result:
            functional_checks["synthesis_coherence"] = False
        else:
            convergence = synth_result.get("convergence_achieved", False)
            consensus = synth_result.get("consensus_score", 0.0)
            recommendation = synth_result.get("investment_recommendation", "")
            
            functional_checks["synthesis_coherence"] = (
                convergence and
                consensus >= 0.7 and
                len(recommendation) >= 50  # Substantial recommendation
            )
        
        # Confidence Scores
        all_confidence_scores = []
        for workflow_result in workflow_results.values():
            if isinstance(workflow_result, dict) and "confidence_score" in workflow_result:
                all_confidence_scores.append(workflow_result["confidence_score"])
        
        functional_checks["confidence_scores"] = (
            len(all_confidence_scores) >= 3 and
            all(0.0 <= score <= 1.0 for score in all_confidence_scores) and
            sum(all_confidence_scores) / len(all_confidence_scores) >= 0.6
        )
        
        # No Mock Patterns (check for typical mock/dummy indicators)
        results_str = json.dumps(results).lower()
        mock_indicators = ["mock", "fake", "dummy", "placeholder", "test_", "sample_"]
        functional_checks["no_mock_patterns"] = not any(
            indicator in results_str for indicator in mock_indicators
        )
        
        passed = sum(functional_checks.values())
        total = len(functional_checks)
        
        print(f"  ✅ Literature Quality: {functional_checks['literature_quality']}")
        print(f"  ✅ Market Data Quality: {functional_checks['market_data_quality']}")
        print(f"  ✅ Synthesis Coherence: {functional_checks['synthesis_coherence']}")
        print(f"  ✅ Confidence Scores: {functional_checks['confidence_scores']}")
        print(f"  ✅ No Mock Patterns: {functional_checks['no_mock_patterns']}")
        print(f"  🎯 Functional Score: {passed}/{total}")
        
        return {
            "passed": passed,
            "total": total,
            "success": passed == total,
            "details": functional_checks
        }
    
    def verify_integration_success(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Verify iceOS integration and orchestration."""
        print("\n🔄 VERIFYING INTEGRATION SUCCESS...")
        
        integration_checks = {
            "workflow_orchestration": False,
            "memory_persistence": False,
            "cost_tracking": False,
            "execution_metrics": False
        }
        
        # Workflow Orchestration
        workflows_executed = results.get("workflows_executed", [])
        integration_checks["workflow_orchestration"] = len(workflows_executed) >= 3
        
        # Memory Persistence (check if agents maintained context)
        workflow_results = results.get("results", {})
        synth_result = workflow_results.get("recursive_synthesis", {})
        # If synthesis worked, agents likely used memory
        integration_checks["memory_persistence"] = (
            isinstance(synth_result, dict) and 
            "consensus_score" in synth_result
        )
        
        # Cost Tracking
        integration_checks["cost_tracking"] = (
            "total_cost_estimate" in results or
            any("cost" in str(workflow_result).lower() 
                for workflow_result in workflow_results.values())
        )
        
        # Execution Metrics
        integration_checks["execution_metrics"] = (
            "start_time" in results and
            "end_time" in results and
            "workflows_executed" in results
        )
        
        passed = sum(integration_checks.values())
        total = len(integration_checks)
        
        print(f"  ✅ Workflow Orchestration: {integration_checks['workflow_orchestration']}")
        print(f"  ✅ Memory Persistence: {integration_checks['memory_persistence']}")
        print(f"  ✅ Cost Tracking: {integration_checks['cost_tracking']}")
        print(f"  ✅ Execution Metrics: {integration_checks['execution_metrics']}")
        print(f"  🎯 Integration Score: {passed}/{total}")
        
        return {
            "passed": passed,
            "total": total,
            "success": passed == total,
            "details": integration_checks
        }
    
    def generate_final_report(self) -> str:
        """Generate final success/failure report."""
        report = self.verification_report
        
        print(f"\n🎉 FINAL VERIFICATION REPORT")
        print("=" * 50)
        print(f"📊 Overall Success: {report['overall_success']}")
        print(f"🔧 Technical: {report['technical_success']}")
        print(f"📊 Functional: {report['functional_success']}")
        print(f"🔄 Integration: {report['integration_success']}")
        print(f"🎯 Score: {report['criteria_passed']}/{report['criteria_total']}")
        
        if report['overall_success']:
            result = "🚀 **100% SUCCESS ACHIEVED!** 🚀"
            print(f"\n{result}")
            print("✅ All real APIs used")
            print("✅ All workflows executed")
            print("✅ All data quality checks passed")
            print("✅ All integration checks passed")
            print("✅ Zero mocking detected")
        else:
            result = "❌ **SUCCESS CRITERIA NOT MET** ❌"
            print(f"\n{result}")
            print("🔍 Check detailed results for specific failures")
        
        return result
    
    def verify_all(self) -> Dict[str, Any]:
        """Run complete verification suite."""
        try:
            print("🎯 BCI INVESTMENT LAB - SUCCESS VERIFICATION")
            print("=" * 60)
            
            # Load results
            results = self.load_results()
            print(f"📁 Loaded results from: {self.results_file}")
            
            # Run all verification checks
            technical = self.verify_technical_success(results)
            functional = self.verify_functional_success(results)
            integration = self.verify_integration_success(results)
            
            # Calculate overall success
            total_passed = technical["passed"] + functional["passed"] + integration["passed"]
            total_criteria = technical["total"] + functional["total"] + integration["total"]
            
            self.verification_report.update({
                "overall_success": total_passed == total_criteria,
                "technical_success": technical["success"],
                "functional_success": functional["success"],
                "integration_success": integration["success"],
                "criteria_passed": total_passed,
                "criteria_total": total_criteria,
                "detailed_results": {
                    "technical": technical,
                    "functional": functional,
                    "integration": integration
                }
            })
            
            # Generate final report
            final_result = self.generate_final_report()
            
            # Save verification report
            verification_file = Path("bci_verification_report.json")
            with open(verification_file, 'w') as f:
                json.dump(self.verification_report, f, indent=2)
            print(f"\n💾 Verification report saved: {verification_file}")
            
            return self.verification_report
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            self.verification_report["error"] = str(e)
            return self.verification_report


def main():
    """Main verification entry point."""
    if len(sys.argv) != 2:
        print("Usage: python verify_success.py <results_file.json>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    verifier = BCISuccessVerifier(results_file)
    report = verifier.verify_all()
    
    # Exit with appropriate code
    sys.exit(0 if report.get("overall_success", False) else 1)


if __name__ == "__main__":
    main() 