"""
🔗 Auto-Workflow Hooks System
============================

Automatically triggers built-in tools after workflow execution.
Provides seamless post-execution analysis without user intervention.

Key Features:
- Automatic post-execution triggering
- Event-driven tool execution
- Configurable hook priorities
- Error-resilient execution
- Results aggregation
"""

from typing import Any, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WorkflowHookManager:
    """Manager for automatic post-execution workflow hooks."""
    
    def __init__(self):
        self.hooks: List[WorkflowHook] = []
        self.enabled = True
    
    def register_hook(self, hook: 'WorkflowHook') -> None:
        """Register a new workflow hook."""
        self.hooks.append(hook)
        # Sort by priority (higher first)
        self.hooks.sort(key=lambda h: h.priority, reverse=True)
    
    async def execute_hooks(self, execution_trace: Dict, workflow_result: Dict) -> Dict[str, Any]:
        """Execute all registered hooks after workflow completion."""
        if not self.enabled:
            return {"status": "disabled", "hooks_executed": 0}
        
        hook_results = {}
        successful_hooks = 0
        failed_hooks = 0
        
        logger.info(f"Executing {len(self.hooks)} post-execution hooks")
        
        for hook in self.hooks:
            try:
                logger.debug(f"Executing hook: {hook.name}")
                start_time = datetime.now()
                
                result = await hook.execute(execution_trace, workflow_result)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                hook_results[hook.name] = {
                    "status": "success",
                    "result": result,
                    "execution_time": execution_time
                }
                successful_hooks += 1
                
                logger.debug(f"Hook {hook.name} completed in {execution_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Hook {hook.name} failed: {e}")
                hook_results[hook.name] = {
                    "status": "error",
                    "error": str(e),
                    "execution_time": 0
                }
                failed_hooks += 1
        
        return {
            "status": "completed",
            "hooks_executed": len(self.hooks),
            "successful_hooks": successful_hooks,
            "failed_hooks": failed_hooks,
            "hook_results": hook_results,
            "execution_timestamp": datetime.now().isoformat()
        }
    
    def disable_hooks(self) -> None:
        """Disable automatic hook execution."""
        self.enabled = False
    
    def enable_hooks(self) -> None:
        """Enable automatic hook execution."""
        self.enabled = True


class WorkflowHook:
    """Base class for workflow execution hooks."""
    
    def __init__(self, name: str, priority: int = 50):
        self.name = name
        self.priority = priority  # Higher = executed first
    
    async def execute(self, execution_trace: Dict, workflow_result: Dict) -> Any:
        """Execute the hook. Override in subclasses."""
        raise NotImplementedError


# Removed MermaidGenerationHook - mermaid generation now happens during blueprint validation
# via the BlueprintVisualizationTool instead of post-execution


class ExecutionSummaryHook(WorkflowHook):
    """Hook that automatically generates execution summaries."""
    
    def __init__(self, priority: int = 90):
        super().__init__("execution_summary", priority)
    
    async def execute(self, execution_trace: Dict, workflow_result: Dict) -> Dict[str, Any]:
        """Generate execution summary automatically."""
        from ice_sdk.tools.builtin.execution_summarizer import ExecutionSummarizerTool
        
        tool = ExecutionSummarizerTool()
        return await tool.execute(
            execution_trace=execution_trace,
            workflow_result=workflow_result,
            summary_type="executive",
            include_recommendations=True
        )


class PerformanceAnalysisHook(WorkflowHook):
    """Hook that automatically performs performance analysis."""
    
    def __init__(self, priority: int = 80):
        super().__init__("performance_analysis", priority)
    
    async def execute(self, execution_trace: Dict, workflow_result: Dict) -> Dict[str, Any]:
        """Perform performance analysis automatically."""
        from ice_sdk.tools.builtin.workflow_analyzer import WorkflowAnalyzerTool
        
        tool = WorkflowAnalyzerTool()
        return await tool.execute(
            execution_trace=execution_trace,
            workflow_result=workflow_result,
            analysis_depth="detailed",
            focus_areas=["performance", "agents", "resources"]
        )


class ComprehensiveProfilingHook(WorkflowHook):
    """Hook that automatically performs comprehensive profiling."""
    
    def __init__(self, priority: int = 70):
        super().__init__("comprehensive_profiling", priority)
    
    async def execute(self, execution_trace: Dict, workflow_result: Dict) -> Dict[str, Any]:
        """Perform comprehensive profiling automatically."""
        from ice_sdk.tools.builtin.performance_profiler import PerformanceProfilerTool
        
        tool = PerformanceProfilerTool()
        return await tool.execute(
            execution_trace=execution_trace,
            workflow_result=workflow_result,
            profiling_depth="detailed",
            focus_metrics=["timing", "resources", "efficiency"]
        )


# Global hook manager instance
global_hook_manager = WorkflowHookManager()

# Auto-register default hooks
def _register_default_hooks():
    """Register the default set of post-execution hooks."""
    global_hook_manager.register_hook(MermaidGenerationHook())
    global_hook_manager.register_hook(ExecutionSummaryHook())
    global_hook_manager.register_hook(PerformanceAnalysisHook())
    global_hook_manager.register_hook(ComprehensiveProfilingHook())

# Auto-register default hooks only if configuration allows
def _maybe_register_default_hooks():
    """Register default hooks only if auto-registration is enabled."""
    from .config import get_config
    config = get_config()
    
    if config.auto_register_hooks:
        _register_default_hooks()

# Check configuration on import
_maybe_register_default_hooks()


# Convenience functions
async def execute_post_workflow_analysis(execution_trace: Dict, workflow_result: Dict) -> Dict[str, Any]:
    """Execute comprehensive post-workflow analysis using all hooks.
    
    Args:
        execution_trace: Workflow execution trace data
        workflow_result: Final workflow result data
        
    Returns:
        Comprehensive analysis results from all hooks
    """
    return await global_hook_manager.execute_hooks(execution_trace, workflow_result)


def register_custom_hook(hook: WorkflowHook) -> None:
    """Register a custom workflow hook.
    
    Args:
        hook: Custom hook instance to register
    """
    global_hook_manager.register_hook(hook)


def disable_auto_analysis() -> None:
    """Disable automatic post-execution analysis."""
    global_hook_manager.disable_hooks()


def enable_auto_analysis() -> None:
    """Enable automatic post-execution analysis."""
    global_hook_manager.enable_hooks()


__all__ = [
    "WorkflowHookManager",
    "WorkflowHook", 
    "MermaidGenerationHook",
    "ExecutionSummaryHook",
    "PerformanceAnalysisHook",
    "ComprehensiveProfilingHook",
    "global_hook_manager",
    "execute_post_workflow_analysis",
    "register_custom_hook",
    "disable_auto_analysis",
    "enable_auto_analysis"
] 