"""
📚 Literature Analysis Workflow
===============================

Comprehensive academic literature analysis with Loop + Parallel processing.

This workflow demonstrates:
- **Loop Nodes**: Iterate through research papers
- **Parallel Nodes**: Multi-source analysis (content, readiness, trends)
- **Condition Nodes**: Quality gates and error handling
- **Agent Nodes**: Expert synthesis with memory
- **Tool Nodes**: arXiv search, statistical analysis, technology readiness
- **LLM Nodes**: Report generation and synthesis

Flow Pattern:
Research Query → arXiv Search → Loop(Papers) → Parallel(Analysis) → Agent Synthesis → Report
"""

from ice_orchestrator.workflow import Workflow
from ice_core.models.node_models import (
    ToolNodeConfig, AgentNodeConfig, LLMOperatorConfig,
    LoopNodeConfig, ParallelNodeConfig, ConditionNodeConfig
)
from use_cases.BCIInvestmentLab.agents import NeuroscienceResearcherConfig


def create_literature_analysis_workflow() -> Workflow:
    """Create sophisticated literature analysis workflow with Loop + Parallel patterns.
    
    Returns:
        Configured workflow for comprehensive literature analysis
    """
    
    nodes = [
        # 1. arXiv Literature Search
        ToolNodeConfig(
            id="arxiv_search",
            type="tool",
            tool_name="arxiv_search",
            tool_args={
                "query": "{{inputs.research_query}}",
                "max_results": "{{inputs.paper_limit}}",
                "date_filter": "{{inputs.time_horizon}}"
            },
            output_schema={"papers": "list", "search_metadata": "dict"},
            description="Search academic literature from arXiv"
        ),
        
        # 2. Paper Quality Filter (Condition Node)
        ConditionNodeConfig(
            id="quality_filter",
            type="condition",
            condition="len(arxiv_search.papers) > 0",
            true_branch="paper_loop",
            false_branch="empty_results_handler",
            dependencies=["arxiv_search"],
            description="Filter papers by quality and relevance"
        ),
        
        # 3. Empty Results Handler (LLM Node)
        LLMOperatorConfig(
            id="empty_results_handler", 
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""No papers found for query: {{inputs.research_query}}
            
Suggest:
1. Alternative search strategies
2. Related research topics
3. Different time horizons
4. Broader or narrower query terms""",
            temperature=0.3,
            dependencies=["quality_filter"],
            output_schema={"suggestions": "list", "alternative_queries": "list"},
            description="Handle empty search results"
        ),
        
        # 4. Paper Processing Loop
        LoopNodeConfig(
            id="paper_loop",
            type="loop",
            loop_over="arxiv_search.papers",
            loop_variable="current_paper",
            loop_body=["parallel_analysis"],
            max_iterations=50,
            dependencies=["quality_filter"],
            description="Loop through each paper for detailed analysis"
        ),
        
        # 5. Parallel Analysis of Each Paper
        ParallelNodeConfig(
            id="parallel_analysis",
            type="parallel",
            parallel_branches=[
                # Content Analysis Branch
                {
                    "branch_id": "content_analysis",
                    "node_config": ToolNodeConfig(
                        id="content_analysis_tool",
                        type="tool",
                        tool_name="statistical_analyzer",
                        tool_args={
                            "data": "{{current_paper}}",
                            "analysis_type": "research_content",
                            "focus_areas": "{{inputs.focus_areas}}"
                        }
                    )
                },
                # Technology Readiness Branch
                {
                    "branch_id": "readiness_assessment", 
                    "node_config": ToolNodeConfig(
                        id="readiness_assessment_tool",
                        type="tool",
                        tool_name="technology_readiness",
                        tool_args={
                            "technology_name": "{{current_paper.title}}",
                            "research_papers": ["{{current_paper}}"],
                            "evaluation_criteria": ["research_maturity", "clinical_potential"]
                        }
                    )
                },
                # Trend Extraction Branch
                {
                    "branch_id": "trend_extraction",
                    "node_config": LLMOperatorConfig(
                        id="trend_extraction_llm",
                        type="llm",
                        model="claude-3-5-sonnet-20241022",
                        prompt_template="""Analyze this research paper for trends and breakthrough indicators:

Title: {{current_paper.title}}
Abstract: {{current_paper.abstract}}
Authors: {{current_paper.authors}}

Extract:
1. Key methodological advances
2. Breakthrough potential indicators
3. Clinical application implications  
4. Technology readiness signals

Focus areas: {{inputs.focus_areas}}""",
                        temperature=0.2
                    )
                }
            ],
            dependencies=["paper_loop"],
            scope="loop",
            description="Parallel analysis of paper content, readiness, and trends"
        ),
        
        # 6. Loop Results Aggregation
        ToolNodeConfig(
            id="results_aggregation",
            type="tool", 
            tool_name="statistical_analyzer",
            tool_args={
                "data": "{{paper_loop.collected_outputs}}",
                "analysis_type": "literature_synthesis",
                "focus_areas": "{{inputs.focus_areas}}"
            },
            dependencies=["paper_loop"],
            output_schema={"synthesis": "dict", "patterns": "list", "trends": "list"},
            description="Aggregate analysis results from all papers"
        ),
        
        # 7. Expert Agent Synthesis
        AgentNodeConfig(
            id="agent_synthesis",
            type="agent",
            package="use_cases.BCIInvestmentLab.agents.neuroscience_researcher",
            agent_attr="NeuroscienceResearcher",
            agent_config={
                "synthesis_mode": True,
                "focus_areas": "{{inputs.focus_areas}}",
                "analysis_depth": "{{inputs.analysis_depth}}"
            },
            dependencies=["results_aggregation"],
            output_schema={"research_insights": "dict", "confidence_score": "float"},
            description="Expert agent synthesis of all literature findings"
        ),
        
        # 8. Final Report Generation
        LLMOperatorConfig(
            id="report_generation",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Generate comprehensive literature analysis report:

Research Query: {{inputs.research_query}}
Papers Analyzed: {{arxiv_search.papers | length}}
Statistical Analysis: {{results_aggregation.synthesis}}
Expert Synthesis: {{agent_synthesis.research_insights}}

# Literature Analysis Report: {{inputs.research_query}}

## Executive Summary
[2-3 sentence overview of key findings]

## Research Landscape
[Analysis of papers, key authors, institutions]

## Key Findings
[Top 5-7 most significant findings]

## Emerging Trends
[3-5 emerging trends identified]

## Technology Readiness Assessment
[Summary of technology maturity]

## Breakthrough Indicators
[Specific breakthrough indicators]

## Research Gaps and Opportunities
[Areas lacking research]

## Recommendations
[Strategic recommendations]

## Methodology
[Analysis methodology description]""",
            temperature=0.2,
            max_tokens=4000,
            dependencies=["agent_synthesis"],
            output_schema={"report": "str", "summary": "dict"},
            description="Generate comprehensive literature analysis report"
        )
    ]
    
    # Create workflow with proper iceOS pattern
    workflow = Workflow(
        nodes=nodes,
        name="literature_analysis",
        version="1.0.0",
        max_parallel=3,
        failure_policy="continue_possible"
    )
    
    return workflow


def create_quick_literature_scan() -> Workflow:
    """Create simplified version for quick literature overview.
    
    Returns:
        Lightweight workflow for rapid literature scanning
    """
    
    nodes = [
        # Quick arXiv search
        ToolNodeConfig(
            id="quick_search",
            type="tool",
            tool_name="arxiv_search",
            tool_args={
                "query": "{{inputs.research_query}}",
                "max_results": 10  # Reduced for speed
            },
            description="Quick arXiv search"
        ),
        
        # Quick analysis
        LLMOperatorConfig(
            id="quick_analysis",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Quick analysis of research papers:

Papers: {{quick_search.papers}}
Query: {{inputs.research_query}}

Generate:
1. Brief overview (2-3 sentences)
2. Top 3 key findings
3. Main research trends
4. Quick breakthrough assessment""",
            dependencies=["quick_search"],
            temperature=0.3,
            description="Quick literature analysis"
        )
    ]
    
    workflow = Workflow(
        nodes=nodes,
        name="quick_literature_scan",
        version="1.0.0"
    )
    
    return workflow


# Export workflows
__all__ = ["create_literature_analysis_workflow", "create_quick_literature_scan"] 