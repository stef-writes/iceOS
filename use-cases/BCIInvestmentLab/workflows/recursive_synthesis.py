"""
🔄 Recursive Synthesis Workflow
==============================

Iterative investment insight refinement through Recursive + Agent Communication.

This workflow demonstrates:
- **Recursive Nodes**: Agent-to-agent communication until convergence
- **Agent Nodes**: Coordination between neuroscience researcher and market intelligence  
- **Workflow Nodes**: Sub-workflow composition (Literature + Market analysis)
- **Condition Nodes**: Convergence detection, quality gates, risk validation
- **LLM Nodes**: Synthesis, analysis, and recommendation generation

Flow Pattern:
Investment Query → Sub-workflows → Recursive(Agent Communication) → Convergence → Final Synthesis
"""

from ice_orchestrator.workflow import Workflow
from ice_core.models.node_models import (
    ToolNodeConfig, AgentNodeConfig, LLMOperatorConfig,
    ConditionNodeConfig, RecursiveNodeConfig, WorkflowNodeConfig
)
from use_cases.BCIInvestmentLab.agents import (
    NeuroscienceResearcherConfig, MarketIntelligenceConfig, InvestmentCoordinatorConfig
)


def create_recursive_synthesis_workflow() -> Workflow:
    """Create sophisticated recursive synthesis workflow with agent coordination.
    
    Returns:
        Configured workflow for recursive investment analysis
    """
    
    nodes = [
        # 1. Input Validation and Preprocessing
        ConditionNodeConfig(
            id="input_validation",
            type="condition",
            condition="len(inputs.investment_thesis.strip()) > 10 and inputs.convergence_threshold > 0.5 and inputs.max_iterations > 0",
            true_branch="initial_analysis_parallel",
            false_branch="input_error_handler",
            description="Validate synthesis inputs and parameters"
        ),
        
        # 2. Input Error Handler
        LLMOperatorConfig(
            id="input_error_handler",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Invalid recursive synthesis inputs detected:

Investment Thesis: "{{inputs.investment_thesis}}"
Convergence Threshold: {{inputs.convergence_threshold}}
Max Iterations: {{inputs.max_iterations}}

Provide:
1. Detailed error description
2. Input requirements and constraints
3. Example valid inputs
4. Recommended parameter values""",
            dependencies=["input_validation"],
            temperature=0.2,
            description="Handle invalid synthesis parameters"
        ),
        
        # 3. Initial Analysis - Parallel Sub-workflows
        ParallelNodeConfig(
            id="initial_analysis_parallel",
            type="parallel",
            parallel_branches=[
                # Literature Analysis Branch
                {
                    "branch_id": "literature_analysis",
                    "node_config": WorkflowNodeConfig(
                        id="literature_workflow",
                        type="workflow",
                        workflow_name="literature_analysis",
                        workflow_version="1.0.0",
                        input_mapping={
                            "research_query": "{{inputs.investment_thesis}}",
                            "analysis_depth": "{{inputs.research_depth}}",
                            "focus_areas": "{{inputs.focus_areas}}"
                        }
                    )
                },
                # Market Analysis Branch
                {
                    "branch_id": "market_analysis", 
                    "node_config": WorkflowNodeConfig(
                        id="market_workflow",
                        type="workflow",
                        workflow_name="market_monitoring",
                        workflow_version="1.0.0",
                        input_mapping={
                            "companies": "['NURO', 'GTBP', 'CBDD']",  # BCI-related symbols
                            "focus_sectors": "{{inputs.focus_areas}}",
                            "risk_tolerance": "{{inputs.risk_tolerance}}"
                        }
                    )
                }
            ],
            dependencies=["input_validation"],
            description="Parallel execution of literature and market analysis sub-workflows"
        ),
        
        # 4. Initial Synthesis Quality Check
        ConditionNodeConfig(
            id="synthesis_quality_check",
            type="condition",
            condition="initial_analysis_parallel.literature_analysis.confidence_score > 0.6 and initial_analysis_parallel.market_analysis.confidence_score > 0.6",
            true_branch="recursive_coordination",
            false_branch="quality_improvement",
            dependencies=["initial_analysis_parallel"],
            description="Check quality of initial analysis before recursive coordination"
        ),
        
        # 5. Quality Improvement
        LLMOperatorConfig(
            id="quality_improvement",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Initial analysis quality below threshold for recursive synthesis:

Literature Analysis Confidence: {{initial_analysis_parallel.literature_analysis.confidence_score}}
Market Analysis Confidence: {{initial_analysis_parallel.market_analysis.confidence_score}}

Analysis Results: {{initial_analysis_parallel}}

Provide quality enhancement strategies:
1. Identify specific data gaps
2. Suggest additional research directions
3. Recommend parameter adjustments
4. Provide enhanced analysis focus areas
5. Generate improved search queries

Goal: Achieve >0.6 confidence for recursive coordination readiness.""",
            dependencies=["synthesis_quality_check"],
            temperature=0.3,
            description="Enhance analysis quality for recursive coordination"
        ),
        
        # 6. Recursive Agent Coordination
        RecursiveNodeConfig(
            id="recursive_coordination",
            type="recursive",
            recursive_body="agent_coordination_round",
            convergence_condition="coordination_round.consensus_score >= inputs.convergence_threshold",
            max_iterations="{{inputs.max_iterations}}",
            iteration_variable="iteration_count",
            state_variables=["research_insights", "market_insights", "consensus_score"],
            initial_state={
                "research_insights": "{{initial_analysis_parallel.literature_analysis}}",
                "market_insights": "{{initial_analysis_parallel.market_analysis}}",
                "consensus_score": 0.0
            },
            dependencies=["synthesis_quality_check", "quality_improvement"],
            description="Recursive agent coordination until convergence"
        ),
        
        # 7. Agent Coordination Round (within recursive loop)
        AgentNodeConfig(
            id="agent_coordination_round",
            type="agent",
            package="use_cases.BCIInvestmentLab.agents.investment_coordinator",
            agent_attr="InvestmentCoordinator",
            agent_config={
                "coordination_mode": "recursive",
                "previous_insights": "{{recursive_state}}",
                "iteration_count": "{{iteration_count}}",
                "convergence_target": "{{inputs.convergence_threshold}}"
            },
            dependencies=["recursive_coordination"],
            scope="recursive",
            output_schema={"consensus_score": "float", "coordination_summary": "dict"},
            description="Single round of agent coordination within recursive loop"
        ),
        
        # 8. Convergence Assessment
        LLMOperatorConfig(
            id="convergence_assessment",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Assess convergence of recursive agent coordination:

Iteration: {{recursive_coordination.current_iteration}}
Max Iterations: {{inputs.max_iterations}}
Target Threshold: {{inputs.convergence_threshold}}

Coordination Results: {{recursive_coordination.final_state}}

Final Consensus Score: {{recursive_coordination.final_state.consensus_score}}
Convergence Achieved: {{recursive_coordination.converged}}

Provide assessment:
1. Convergence quality analysis
2. Consensus strength evaluation
3. Areas of remaining disagreement
4. Confidence in final synthesis
5. Recommendations for decision making

If convergence not achieved, explain limitations and next steps.""",
            dependencies=["recursive_coordination"],
            temperature=0.2,
            description="Assess quality and completeness of convergence"
        ),
        
        # 9. Decision Quality Gate
        ConditionNodeConfig(
            id="decision_quality_gate",
            type="condition",
            condition="recursive_coordination.converged or recursive_coordination.final_state.consensus_score >= 0.7",
            true_branch="final_synthesis",
            false_branch="forced_resolution",
            dependencies=["convergence_assessment"],
            description="Determine if synthesis quality is sufficient for final decision"
        ),
        
        # 10. Forced Resolution (when convergence fails)
        LLMOperatorConfig(
            id="forced_resolution",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Recursive coordination did not achieve full convergence. Generate forced resolution:

Convergence Status: {{recursive_coordination.converged}}
Final Consensus Score: {{recursive_coordination.final_state.consensus_score}}
Iterations Completed: {{recursive_coordination.current_iteration}}

Final Agent States: {{recursive_coordination.final_state}}

Despite incomplete convergence, synthesize:
1. Areas of strong agreement
2. Key points of disagreement
3. Weighted synthesis approach
4. Risk-adjusted recommendations
5. Decision framework with uncertainty handling

Investment Thesis: {{inputs.investment_thesis}}
Risk Tolerance: {{inputs.risk_tolerance}}""",
            dependencies=["decision_quality_gate"],
            temperature=0.3,
            max_tokens=4000,
            description="Generate investment synthesis when convergence is incomplete"
        ),
        
        # 11. Final Investment Synthesis
        LLMOperatorConfig(
            id="final_synthesis",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Generate final investment synthesis from converged recursive coordination:

Original Investment Thesis: {{inputs.investment_thesis}}
Convergence Achieved: {{recursive_coordination.converged}}
Final Consensus Score: {{recursive_coordination.final_state.consensus_score}}

Coordination Results: {{recursive_coordination.final_state}}
Convergence Assessment: {{convergence_assessment.assessment}}

# Investment Thesis Analysis: {{inputs.investment_thesis}}

## Executive Summary
[2-3 sentence thesis validation/refinement]

## Research Foundation
[Synthesis of literature analysis findings]

## Market Validation
[Market intelligence and opportunity assessment]

## Convergence Analysis
[Agent consensus and coordination insights]

## Investment Recommendation
[Clear invest/don't invest recommendation with rationale]

## Risk Assessment
[Comprehensive risk analysis and mitigation strategies]

## Implementation Strategy
[If investing, provide implementation approach]

## Monitoring and Adjustments
[Ongoing monitoring recommendations]

## Confidence Assessment
[Overall confidence in recommendation and key assumptions]

Investment Amount Considered: ${{inputs.investment_amount}}
Risk Tolerance: {{inputs.risk_tolerance}}""",
            dependencies=["decision_quality_gate"],
            temperature=0.2,
            max_tokens=5000,
            description="Generate comprehensive final investment synthesis"
        ),
        
        # 12. Risk Validation Check
        ConditionNodeConfig(
            id="risk_validation",
            type="condition",
            condition="recursive_coordination.final_state.risk_assessment.overall_risk != 'high' or inputs.risk_tolerance == 'high'",
            true_branch="recommendation_generation",
            false_branch="risk_override_analysis",
            dependencies=["final_synthesis", "forced_resolution"],
            description="Validate risk levels against tolerance"
        ),
        
        # 13. Risk Override Analysis
        LLMOperatorConfig(
            id="risk_override_analysis",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""High risk detected with moderate/low risk tolerance. Provide override analysis:

Risk Assessment: {{recursive_coordination.final_state.risk_assessment}}
Risk Tolerance: {{inputs.risk_tolerance}}
Investment Amount: ${{inputs.investment_amount}}

Final Synthesis: {{final_synthesis.synthesis}}

Provide risk override considerations:
1. Specific high-risk factors
2. Risk mitigation strategies
3. Position sizing adjustments
4. Alternative investment approaches
5. Wait-and-see recommendations
6. Risk monitoring requirements

Recommendation: Should investment proceed despite risk mismatch?""",
            dependencies=["risk_validation"],
            temperature=0.2,
            description="Analyze risk override options"
        ),
        
        # 14. Final Recommendation Generation
        LLMOperatorConfig(
            id="recommendation_generation",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Generate final investment recommendation based on complete analysis:

Investment Thesis: {{inputs.investment_thesis}}
Final Synthesis: {{final_synthesis.synthesis}}
Forced Resolution: {{forced_resolution.resolution}}
Risk Override: {{risk_override_analysis.override}}

Convergence Details:
- Achieved: {{recursive_coordination.converged}}
- Consensus Score: {{recursive_coordination.final_state.consensus_score}}
- Iterations: {{recursive_coordination.current_iteration}}

**INVESTMENT RECOMMENDATION**: [INVEST/DON'T INVEST/WAIT]

**Rationale**: [2-3 sentence justification]

**Position Size**: [Recommended investment amount]

**Timeline**: [Investment timeline and milestones]

**Key Success Factors**: [3-5 critical success factors]

**Risk Mitigation**: [Primary risk management strategies]

**Exit Strategy**: [When and how to exit]

**Monitoring Plan**: [What to monitor post-investment]

**Confidence Level**: [High/Medium/Low with explanation]""",
            dependencies=["risk_validation", "risk_override_analysis"],
            temperature=0.2,
            output_schema={"recommendation": "str", "confidence": "float", "action": "str"},
            description="Generate final actionable investment recommendation"
        )
    ]
    
    # Create workflow with proper iceOS pattern
    workflow = Workflow(
        nodes=nodes,
        name="recursive_synthesis",
        version="1.0.0",
        max_parallel=2,  # Allow parallel sub-workflows
        failure_policy="continue_possible"
    )
    
    return workflow


def create_simple_consensus_workflow() -> Workflow:
    """Create simplified version for basic agent consensus.
    
    Returns:
        Lightweight workflow for basic agent agreement
    """
    
    nodes = [
        # Research agent analysis
        AgentNodeConfig(
            id="research_analysis",
            type="agent",
            package="use_cases.BCIInvestmentLab.agents.neuroscience_researcher",
            agent_attr="NeuroscienceResearcher",
            description="Research agent analysis"
        ),
        
        # Market agent analysis 
        AgentNodeConfig(
            id="market_analysis",
            type="agent",
            package="use_cases.BCIInvestmentLab.agents.market_intelligence",
            agent_attr="MarketIntelligenceAgent",
            description="Market agent analysis"
        ),
        
        # Simple coordination
        AgentNodeConfig(
            id="simple_coordination",
            type="agent",
            package="use_cases.BCIInvestmentLab.agents.investment_coordinator",
            agent_attr="InvestmentCoordinator",
            agent_config={"coordination_mode": "simple"},
            dependencies=["research_analysis", "market_analysis"],
            description="Simple agent coordination"
        )
    ]
    
    workflow = Workflow(
        nodes=nodes,
        name="simple_consensus",
        version="1.0.0"
    )
    
    return workflow


# Export workflows
__all__ = ["create_recursive_synthesis_workflow", "create_simple_consensus_workflow"] 