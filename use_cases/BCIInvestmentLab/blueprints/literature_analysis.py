"""Literature Analysis Blueprint - Complete Node Type Implementation"""

from ice_core.models.mcp import Blueprint, NodeSpec


def create_literature_analysis_blueprint(research_topic: str = "brain-computer interfaces") -> Blueprint:
    """Literature analysis with complete node type demonstration.
    
    Node types used: tool, condition, llm, loop, parallel, agent
    """
    
    return Blueprint(
        blueprint_id=f"literature_analysis_{hash(research_topic) % 10000}",
        nodes=[
            # 1. TOOL: arXiv search
            NodeSpec(
                id="arxiv_search",
                type="tool",
                tool_name="arxiv_search",
                tool_args={
                    "query": research_topic,
                    "max_results": 10,
                    "sort_by": "relevance"
                }
            ),
            
            # 2. CONDITION: Check if papers found
            NodeSpec(
                id="papers_validation",
                type="condition",
                dependencies=["arxiv_search"],
                expression="len(arxiv_search.papers) > 0",
                true_branch=["parallel_analysis"],
                false_branch=["no_papers_found"],
                input_schema={"arxiv_search": "object"},
                output_schema={"condition_result": "boolean"}
            ),
            
            # 3. LLM: Handle no papers case
            NodeSpec(
                id="no_papers_found",
                type="llm",
                model="gpt-4o",
                prompt=f"No papers found for '{research_topic}'. Suggest alternative search terms and research directions.",
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 300
                }
            ),
            
            # 4a. TOOL: Technical analysis
            NodeSpec(
                id="technical_analysis",
                type="tool",
                tool_name="statistical_analyzer",
                tool_args={"papers": "{{arxiv_search.papers}}", "focus": "technical"}
            ),
            
            # 4b. TOOL: Trend analysis  
            NodeSpec(
                id="trend_analysis",
                type="tool", 
                tool_name="trend_analyzer",
                tool_args={"papers": "{{arxiv_search.papers}}", "focus": "trends"}
            ),
            
            # 4c. PARALLEL: Execute analyses concurrently
            NodeSpec(
                id="parallel_analysis",
                type="parallel",
                dependencies=["papers_validation"],
                branches=[
                    ["technical_analysis"],
                    ["trend_analysis"]
                ],
                max_concurrency=2
            ),
            
            # 5a. TOOL: Paper analyzer for loop
            NodeSpec(
                id="paper_analyzer",
                type="tool",
                tool_name="technology_readiness", 
                tool_args={"paper": "{{item}}", "analysis_depth": "detailed"}
            ),
            
            # 5b. LOOP: Process each paper individually
            NodeSpec(
                id="paper_processing_loop",
                type="loop",
                dependencies=["parallel_analysis"],
                items_source="arxiv_search.papers",
                item_var="item",
                body_nodes=["paper_analyzer"],
                max_iterations=10
            ),
            
            # 6. AGENT: Research analysis
            NodeSpec(
                id="research_analysis",
                type="agent",
                package="neuroscience_researcher",
                dependencies=["paper_processing_loop"],
                agent_config={
                    "research_focus": research_topic,
                    "analysis_depth": "comprehensive",
                    "memory_enabled": True
                },
                input_schema={"papers": "array", "loop_results": "array"},
                output_schema={"analysis": "object", "insights": "array"}
            ),
            
            # 7. LLM: Final synthesis
            NodeSpec(
                id="literature_synthesis",
                type="llm",
                model="gpt-4o",
                dependencies=["research_analysis"],
                prompt=f"""Synthesize literature analysis for {research_topic}.

Technical Analysis: {{{{parallel_analysis.technical_analysis}}}}
Trend Analysis: {{{{parallel_analysis.trend_analysis}}}}
Individual Papers: {{{{paper_processing_loop.results}}}}
Agent Analysis: {{{{research_analysis.analysis}}}}

Provide comprehensive literature review with investment implications.""",
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            )
        ],
        metadata={
            "workflow_type": "literature_analysis",
            "research_topic": research_topic,
            "node_types_used": ["tool", "condition", "llm", "loop", "parallel", "agent"],
            "estimated_duration": "3-5 minutes"
        }
    ) 