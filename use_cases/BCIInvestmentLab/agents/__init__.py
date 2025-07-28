"""
🤖 BCI Investment Lab - Intelligent Agents
=========================================

This package contains specialized agents for BCI investment research:

## Stateful Agents (with Memory)

### 1. Neuroscience Researcher Agent 
- **Memory Types**: ALL 4 types (Working, Episodic, Semantic, Procedural)
- **Purpose**: Analyze academic research, track breakthroughs, assess technology readiness
- **Tools**: arXiv search, statistical analysis, technology readiness assessment
- **Specialization**: Deep understanding of BCI technology and neuroscience research

### 2. Market Intelligence Agent
- **Memory Types**: Economic memory (Episodic, Semantic, Procedural)
- **Purpose**: Track market trends, company analysis, investment signals
- **Tools**: Yahoo Finance, Reddit sentiment, company research, trend analysis
- **Specialization**: Financial markets, investment analysis, economic indicators

### 3. Investment Coordinator Agent (Recursive)
- **Memory Types**: Strategic memory for coordination
- **Purpose**: Synthesize research and market insights, make investment recommendations
- **Capability**: Recursive agent-to-agent communication until convergence
- **Specialization**: Investment thesis development, risk assessment, timing

## Stateless LLM Nodes

### 4. Literature Synthesizer
- **Type**: Pure LLM node with tools (no memory)
- **Purpose**: Synthesize research findings into coherent insights
- **Tools**: Statistical analyzer, trend analyzer

### 5. Investment Thesis Generator  
- **Type**: Pure LLM node with tools (no memory)
- **Purpose**: Generate investment recommendations and reports
- **Tools**: Company research, technology readiness

## Agent Communication Patterns

The agents are designed to communicate and collaborate:

```
Neuroscience Researcher ←→ Market Intelligence Agent
                     ↓              ↓
                Investment Coordinator (Recursive)
                         ↓
              Literature Synthesizer + Thesis Generator
```

## Memory Architecture

Each agent leverages iceOS's 4-tier memory system:

- **Working Memory**: Current session context and active tasks
- **Episodic Memory**: Events, research sessions, market events  
- **Semantic Memory**: Domain knowledge, facts, relationships
- **Procedural Memory**: Research methods, analysis patterns, strategies
"""

# Agent implementations
from .neuroscience_researcher import NeuroscienceResearcher, NeuroscienceResearcherConfig
from .market_intelligence import MarketIntelligenceAgent, MarketIntelligenceConfig
from .investment_coordinator import InvestmentCoordinator, InvestmentCoordinatorConfig

__all__ = [
    # Agents
    "NeuroscienceResearcher",
    "MarketIntelligenceAgent", 
    "InvestmentCoordinator",
    # Configs
    "NeuroscienceResearcherConfig",
    "MarketIntelligenceConfig",
    "InvestmentCoordinatorConfig"
] 