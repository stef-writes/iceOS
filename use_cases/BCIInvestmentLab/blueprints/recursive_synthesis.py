"""Recursive Synthesis Blueprint - Advanced iceOS Demonstration"""

from ice_core.models.mcp import Blueprint, NodeSpec


def create_recursive_synthesis_blueprint(research_question: str = "What are the most promising BCI investment opportunities?") -> Blueprint:
    """Advanced recursive synthesis demonstrating sophisticated iceOS capabilities.
    
    Node types used: condition, workflow, recursive, agent, llm
    Shows: recursive conversations, workflow embedding, multi-agent coordination
    """
    
    return Blueprint(
        blueprint_id=f"recursive_synthesis_{hash(research_question) % 10000}",
        nodes=[
            # 1. CONDITION: Input validation
            NodeSpec(
                id="input_validation",
                type="condition",
                expression="len(inputs.research_question.strip()) > 10",
                true_branch=["parallel_research"],
                false_branch=["input_error_handler"],
                input_schema={"research_question": "string"},
                output_schema={"condition_result": "boolean"}
            ),
            
            # 2. LLM: Input error handler
            NodeSpec(
                id="input_error_handler",
                type="llm",
                model="gpt-4o",
                prompt="The research question is too short or invalid. Please provide a more specific investment research question.",
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 200
                }
            ),
            
            # 3a. WORKFLOW: Literature analysis
            NodeSpec(
                id="literature_branch",
                type="workflow",
                workflow_ref="literature_analysis",
                config_overrides={
                    "research_topic": "brain-computer interfaces"
                }
            ),
            
            # 3b. WORKFLOW: Market monitoring
            NodeSpec(
                id="market_branch", 
                type="workflow",
                workflow_ref="market_monitoring",
                config_overrides={
                    "companies": ["NFLX", "META", "GOOGL", "NVDA"]
                }
            ),
            
            # 3c. PARALLEL: Execute research workflows concurrently
            NodeSpec(
                id="parallel_research",
                type="parallel",
                dependencies=["input_validation"],
                branches=[
                    ["literature_branch"],
                    ["market_branch"]
                ],
                max_concurrency=2
            ),
            
            # 4. CONDITION: Research quality check
            NodeSpec(
                id="research_quality_check",
                type="condition",
                dependencies=["parallel_research"],
                expression="parallel_research.literature_branch.status == 'completed' and parallel_research.market_branch.status == 'completed'",
                true_branch=["recursive_synthesis"],
                false_branch=["research_error_handler"],
                input_schema={"parallel_research": "object"},
                output_schema={"condition_result": "boolean"}
            ),
            
            # 5. LLM: Research error handler
            NodeSpec(
                id="research_error_handler", 
                type="llm",
                model="gpt-4o",
                prompt="Some research workflows failed. Proceeding with available data and noting limitations in analysis.",
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4o",
                    "temperature": 0.6,
                    "max_tokens": 300
                }
            ),
            
            # 6. RECURSIVE: Multi-agent conversation until convergence
            NodeSpec(
                id="recursive_synthesis",
                type="recursive",
                dependencies=["research_quality_check"],
                recursive_sources=["research_quality_check"],
                convergence_condition="consensus_score > 0.8",
                max_iterations=3,
                agent_package="investment_coordinator",
                preserve_context=True,
                input_schema={"parallel_research": "object", "research_question": "string"},
                output_schema={"final_consensus": "object", "conversation_history": "array", "converged": "boolean", "consensus_score": "number"}
            ),
            
            # 7. CONDITION: Convergence validation
            NodeSpec(
                id="convergence_validation",
                type="condition",
                dependencies=["recursive_synthesis"],
                expression="recursive_synthesis.converged == true and recursive_synthesis.consensus_score > 0.7",
                true_branch=["final_investment_report"],
                false_branch=["manual_synthesis"],
                input_schema={"recursive_synthesis": "object"},
                output_schema={"condition_result": "boolean"}
            ),
            
            # 8. LLM: Manual synthesis fallback
            NodeSpec(
                id="manual_synthesis",
                type="llm",
                model="gpt-4o",
                prompt=f"""Agent consensus was not reached. Manually synthesize the research for: {research_question}

Literature Analysis: {{{{parallel_research.literature_branch.output}}}}
Market Analysis: {{{{parallel_research.market_branch.output}}}}
Agent Discussions: {{{{recursive_synthesis.conversation_history}}}}

Provide investment synthesis noting areas of disagreement.""",
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4o", 
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            ),
            
            # 9. LLM: Final investment report
            NodeSpec(
                id="final_investment_report",
                type="llm",
                model="gpt-4o",
                dependencies=["convergence_validation"],
                prompt=f"""Generate comprehensive investment report based on recursive synthesis.

Research Question: {research_question}

Literature Findings: {{{{parallel_research.literature_branch.output}}}}
Market Intelligence: {{{{parallel_research.market_branch.output}}}}
Agent Consensus: {{{{recursive_synthesis.final_consensus}}}}
Conversation History: {{{{recursive_synthesis.conversation_history}}}}

Create professional investment thesis with:
1. Executive Summary
2. Research Methodology (literature + market + agent synthesis)
3. Key Technical Findings
4. Market Analysis & Opportunities
5. Multi-Agent Consensus Insights
6. Investment Recommendations
7. Risk Assessment & Mitigation
8. Implementation Timeline
9. Success Metrics

Format as comprehensive investment memorandum.""",
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            ),
            
            # 10. AGENT: Final validation and packaging
            NodeSpec(
                id="report_validation",
                type="agent",
                package="investment_coordinator",
                dependencies=["final_investment_report"],
                agent_config={
                    "task": "final_report_validation",
                    "quality_check": True,
                    "memory_enabled": True
                },
                input_schema={"investment_report": "string"},
                output_schema={"validation_result": "object", "final_report": "string"}
            )
        ],
        metadata={
            "workflow_type": "recursive_synthesis",
            "research_question": research_question,
            "node_types_used": ["condition", "workflow", "recursive", "agent", "llm", "parallel"],
            "complexity": "advanced",
            "estimated_duration": "8-12 minutes",
            "demonstrates": [
                "recursive_agent_conversations",
                "workflow_embedding", 
                "multi_agent_coordination",
                "convergence_detection",
                "conditional_branching"
            ],
            "agents_involved": 4,
            "sub_workflows": 2
        }
    ) 