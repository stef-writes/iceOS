"""
⚡ BCI Investment Lab - Intelligent Workflows
===========================================

This package contains specialized workflows that demonstrate all iceOS node types:

## Core Workflows

### 1. Literature Analysis Workflow
- **Node Types**: Tool, Loop, Parallel, Agent
- **Purpose**: Analyze academic papers and research trends
- **Flow**: arXiv search → Loop through papers → Parallel analysis → Agent synthesis

### 2. Market Monitoring Workflow  
- **Node Types**: Tool, Condition, Parallel, Agent
- **Purpose**: Monitor market conditions and investment signals
- **Flow**: Parallel data fetch → Condition gates → Market analysis → Signal generation

### 3. Recursive Synthesis Workflow
- **Node Types**: Recursive, Agent, Workflow
- **Purpose**: Iterative refinement of investment insights
- **Flow**: Research insights ↔ Market insights → Recursive coordination → Convergence

## Advanced Workflow Features

### Neural Signal Processing (Code Node Demo)
- **Code Node**: Generate synthetic neural signals for validation
- **Purpose**: Demonstrate code execution capabilities
- **Integration**: Feeds into technology readiness assessment

### Report Generation (LLM Nodes Demo)
- **LLM Nodes**: Literature synthesizer + Investment thesis generator
- **Purpose**: Pure text generation with tool access
- **Output**: Comprehensive investment reports

## Workflow Composition Patterns

All workflows can be composed and reused:

```
Literature Analysis ──┐
                      ├─→ Recursive Synthesis ──→ Final Report
Market Monitoring ────┘
```

## iceOS Node Type Coverage

✅ Tool Nodes: All 9 custom tools used across workflows
✅ LLM Nodes: Literature synthesizer, thesis generator  
✅ Agent Nodes: Research, market, coordination agents
✅ Code Nodes: Neural signal simulation
✅ Condition Nodes: Investment viability gates
✅ Loop Nodes: Paper processing, data iteration
✅ Parallel Nodes: Multi-source data fetching
✅ Recursive Nodes: Agent convergence loops
✅ Workflow Nodes: Modular composition

## Workflow Architecture

Each workflow is designed to be:
- **Modular**: Reusable components
- **Scalable**: Parallel execution where possible  
- **Intelligent**: Agent-based reasoning
- **Observable**: Full event streaming and metrics
- **Secure**: WASM isolation for code execution
"""

# Workflow implementations using proper iceOS pattern
from .literature_analysis import (
    create_literature_analysis_workflow,
    create_quick_literature_scan
)
from .market_monitoring import (
    create_market_monitoring_workflow,
    create_simple_market_check
)
from .recursive_synthesis import (
    create_recursive_synthesis_workflow,
    create_simple_consensus_workflow
)

__all__ = [
    # Main sophisticated workflows
    "create_literature_analysis_workflow",
    "create_market_monitoring_workflow", 
    "create_recursive_synthesis_workflow",
    # Simplified variants for quick analysis
    "create_quick_literature_scan",
    "create_simple_market_check",
    "create_simple_consensus_workflow"
] 