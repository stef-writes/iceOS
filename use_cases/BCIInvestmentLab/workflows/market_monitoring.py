"""
📊 Market Monitoring Workflow
============================

Real-time market monitoring with Condition + Tools patterns.

This workflow demonstrates:
- **Condition Nodes**: Market viability gates, alert thresholds, risk gates
- **Parallel Nodes**: Multi-source data fetching (Financial, Sentiment, News)
- **Tool Nodes**: Yahoo Finance, NewsAPI, company research, trend analysis
- **Agent Nodes**: Market intelligence with signal generation
- **LLM Nodes**: Risk analysis and recommendation generation

Flow Pattern:
Market Query → Parallel(Data Sources) → Condition(Viability) → Analysis → Signal Generation
"""

from ice_orchestrator.workflow import Workflow
from ice_core.models.node_models import (
    ToolNodeConfig, AgentNodeConfig, LLMOperatorConfig,
    ConditionNodeConfig, ParallelNodeConfig
)
from use_cases.BCIInvestmentLab.agents import MarketIntelligenceConfig


def create_market_monitoring_workflow() -> Workflow:
    """Create sophisticated market monitoring workflow with Condition + Tools patterns.
    
    Returns:
        Configured workflow for comprehensive market monitoring
    """
    
    nodes = [
        # 1. Market Session Validation
        ConditionNodeConfig(
            id="session_validation",
            type="condition", 
            condition="len(inputs.companies) > 0 and inputs.monitoring_duration in ['1_hour', '1_day', '1_week', '1_month']",
            true_branch="parallel_data_fetch",
            false_branch="invalid_input_handler",
            description="Validate market monitoring session parameters"
        ),
        
        # 2. Invalid Input Handler
        LLMOperatorConfig(
            id="invalid_input_handler",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Invalid market monitoring inputs detected:

Companies: {{inputs.companies}}
Duration: {{inputs.monitoring_duration}}

Provide:
1. Error description
2. Corrected input suggestions  
3. Valid company symbol examples
4. Supported duration options""",
            dependencies=["session_validation"],
            temperature=0.2,
            description="Handle invalid input parameters"
        ),
        
        # 3. Parallel Data Fetching
        ParallelNodeConfig(
            id="parallel_data_fetch",
            type="parallel",
            parallel_branches=[
                # Financial Data Branch
                {
                    "branch_id": "financial_data",
                    "node_config": ToolNodeConfig(
                        id="yahoo_finance_fetch",
                        type="tool",
                        tool_name="yahoo_finance_fetcher",
                        tool_args={
                            "symbols": "{{inputs.companies}}",
                            "period": "{{inputs.monitoring_duration}}",
                            "include_financials": True,
                            "include_analysis": True
                        }
                    )
                },
                # Sentiment Data Branch
                {
                    "branch_id": "sentiment_data",
                    "node_config": ToolNodeConfig(
                        id="newsapi_sentiment_fetch",
                        type="tool", 
                        tool_name="newsapi_sentiment",
                        tool_args={
                            "query": "{{' OR '.join(inputs.companies)}} financial news",
                            "companies": "{{inputs.companies}}",
                            "timeframe": "{{inputs.monitoring_duration}}",
                            "sentiment_focus": "financial",
                            "max_articles": 30
                        }
                    )
                },
                # Tech Sentiment Branch
                {
                    "branch_id": "tech_sentiment",
                    "node_config": ToolNodeConfig(
                        id="hackernews_fetch",
                        type="tool",
                        tool_name="hackernews_tracker", 
                        tool_args={
                            "keywords": "{{inputs.focus_sectors}}",
                            "timeframe": "{{inputs.monitoring_duration}}",
                            "min_score": 5
                        }
                    )
                },
                # Company News Branch
                {
                    "branch_id": "company_news",
                    "node_config": ToolNodeConfig(
                        id="company_research_fetch",
                        type="tool",
                        tool_name="company_research",
                        tool_args={
                            "company_symbols": "{{inputs.companies}}",
                            "research_depth": "news_and_events",
                            "focus_areas": "{{inputs.focus_sectors}}"
                        }
                    )
                }
            ],
            dependencies=["session_validation"],
            description="Parallel fetching of financial, sentiment, and news data"
        ),
        
        # 4. Data Quality Validation
        ConditionNodeConfig(
            id="data_quality_check",
            type="condition",
            condition="parallel_data_fetch.financial_data.success and len(parallel_data_fetch.financial_data.data) > 0",
            true_branch="threshold_analysis",
            false_branch="data_quality_recovery",
            dependencies=["parallel_data_fetch"],
            description="Validate data quality and completeness"
        ),
        
        # 5. Data Quality Recovery
        LLMOperatorConfig(
            id="data_quality_recovery",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Market data quality issues detected:

Financial Data Status: {{parallel_data_fetch.financial_data.success}}
Available Data: {{parallel_data_fetch}}

Provide:
1. Data quality assessment
2. Alternative data sources
3. Partial analysis recommendations
4. Retry suggestions""",
            dependencies=["data_quality_check"],
            temperature=0.3,
            description="Recover from data quality issues"
        ),
        
        # 6. Threshold Analysis and Alert Generation
        ToolNodeConfig(
            id="threshold_analysis",
            type="tool",
            tool_name="trend_analyzer",
            tool_args={
                "financial_data": "{{parallel_data_fetch.financial_data}}",
                "sentiment_data": "{{parallel_data_fetch.sentiment_data}}",
                "alert_thresholds": "{{inputs.alert_thresholds}}",
                "analysis_type": "threshold_monitoring"
            },
            dependencies=["data_quality_check"],
            output_schema={"alerts": "list", "trends": "list", "signals": "list"},
            description="Analyze data against alert thresholds"
        ),
        
        # 7. Alert Condition Gate
        ConditionNodeConfig(
            id="alert_condition_gate",
            type="condition",
            condition="len(threshold_analysis.alerts) > 0",
            true_branch="high_priority_analysis",
            false_branch="routine_monitoring",
            dependencies=["threshold_analysis"],
            description="Route based on alert conditions"
        ),
        
        # 8. High Priority Analysis (Alert Triggered)
        AgentNodeConfig(
            id="high_priority_analysis",
            type="agent",
            package="use_cases.BCIInvestmentLab.agents.market_intelligence",
            agent_attr="MarketIntelligenceAgent",
            agent_config={
                "analysis_priority": "high",
                "alert_mode": True,
                "risk_tolerance": "{{inputs.risk_tolerance}}"
            },
            dependencies=["alert_condition_gate"],
            output_schema={"investment_signals": "list", "risk_assessment": "dict"},
            description="High-priority market intelligence analysis for alerts"
        ),
        
        # 9. Routine Monitoring (No Alerts)
        AgentNodeConfig(
            id="routine_monitoring",
            type="agent",
            package="use_cases.BCIInvestmentLab.agents.market_intelligence",
            agent_attr="MarketIntelligenceAgent",
            agent_config={
                "analysis_priority": "standard",
                "alert_mode": False,
                "risk_tolerance": "{{inputs.risk_tolerance}}"
            },
            dependencies=["alert_condition_gate"],
            output_schema={"investment_signals": "list", "risk_assessment": "dict"},
            description="Standard market intelligence monitoring"
        ),
        
        # 10. Risk Assessment Gate
        ConditionNodeConfig(
            id="risk_assessment_gate",
            type="condition",
            condition="(high_priority_analysis.risk_assessment.overall_risk == 'high') or (routine_monitoring.risk_assessment.overall_risk == 'high')",
            true_branch="risk_mitigation_analysis",
            false_branch="signal_generation",
            dependencies=["high_priority_analysis", "routine_monitoring"],
            description="Assess overall risk level and route accordingly"
        ),
        
        # 11. Risk Mitigation Analysis
        LLMOperatorConfig(
            id="risk_mitigation_analysis",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""High risk conditions detected in market monitoring:

High Priority Analysis: {{high_priority_analysis}}
Routine Monitoring: {{routine_monitoring}}
Alert Thresholds: {{inputs.alert_thresholds}}

Provide risk mitigation strategies:
1. Immediate risk factors
2. Mitigation recommendations
3. Portfolio protection strategies
4. Monitoring frequency adjustments
5. Exit strategies if applicable

Risk Tolerance: {{inputs.risk_tolerance}}""",
            dependencies=["risk_assessment_gate"],
            temperature=0.2,
            description="Generate risk mitigation strategies"
        ),
        
        # 12. Investment Signal Generation
        LLMOperatorConfig(
            id="signal_generation",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Generate investment signals based on market monitoring:

Market Data: {{parallel_data_fetch}}
High Priority Analysis: {{high_priority_analysis}}
Routine Analysis: {{routine_monitoring}}
Threshold Analysis: {{threshold_analysis}}

Generate signals for:
1. Buy opportunities
2. Sell recommendations
3. Hold positions
4. Position sizing adjustments
5. Sector rotation opportunities

Consider:
- Alert thresholds: {{inputs.alert_thresholds}}
- Risk tolerance: {{inputs.risk_tolerance}}
- Monitoring duration: {{inputs.monitoring_duration}}""",
            dependencies=["risk_assessment_gate", "risk_mitigation_analysis"],
            temperature=0.3,
            output_schema={"signals": "list", "recommendations": "list"},
            description="Generate actionable investment signals"
        ),
        
        # 13. Real-time Monitoring Condition
        ConditionNodeConfig(
            id="realtime_condition",
            type="condition",
            condition="inputs.enable_realtime == true",
            true_branch="realtime_alerts",
            false_branch="monitoring_summary",
            dependencies=["signal_generation"],
            description="Check if real-time monitoring is enabled"
        ),
        
        # 14. Real-time Alert System
        LLMOperatorConfig(
            id="realtime_alerts",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Configure real-time monitoring alerts:

Companies: {{inputs.companies}}
Thresholds: {{inputs.alert_thresholds}}
Generated Signals: {{signal_generation.signals}}
Risk Assessment: {{risk_mitigation_analysis.strategies}}

Set up:
1. Real-time price alerts
2. Volume spike notifications
3. Sentiment change alerts
4. News impact notifications
5. Risk threshold breaches""",
            dependencies=["realtime_condition"],
            temperature=0.2,
            description="Configure real-time monitoring and alerts"
        ),
        
        # 15. Monitoring Summary Generation
        LLMOperatorConfig(
            id="monitoring_summary",
            type="llm",
            model="claude-3-5-sonnet-20241022", 
            prompt_template="""Generate comprehensive market monitoring summary:

Session Details:
- Companies: {{inputs.companies}}
- Duration: {{inputs.monitoring_duration}}
- Focus Sectors: {{inputs.focus_sectors}}

Analysis Results:
- Data Quality: {{parallel_data_fetch}}
- Threshold Analysis: {{threshold_analysis}}
- Market Intelligence: {{high_priority_analysis or routine_monitoring}}
- Investment Signals: {{signal_generation.signals}}
- Risk Assessment: {{risk_mitigation_analysis.strategies}}

# Market Monitoring Report

## Executive Summary
[Key market movements and signals]

## Alert Status
[Triggered alerts and responses]

## Investment Signals
[Generated signals and recommendations]

## Risk Assessment
[Current risk levels and factors]

## Next Steps
[Monitoring recommendations]""",
            dependencies=["realtime_condition", "realtime_alerts"],
            temperature=0.2,
            max_tokens=3000,
            output_schema={"summary": "str", "alerts": "list", "next_actions": "list"},
            description="Generate comprehensive monitoring summary"
        )
    ]
    
    # Create workflow with proper iceOS pattern
    workflow = Workflow(
        nodes=nodes,
        name="market_monitoring",
        version="1.0.0",
        max_parallel=4,  # Allow parallel data fetching
        failure_policy="continue_possible"
    )
    
    return workflow


def create_simple_market_check() -> Workflow:
    """Create simplified version for quick market status checks.
    
    Returns:
        Lightweight workflow for rapid market overview
    """
    
    nodes = [
        # Quick financial data fetch
        ToolNodeConfig(
            id="quick_fetch",
            type="tool",
            tool_name="yahoo_finance_fetcher",
            tool_args={
                "symbols": "{{inputs.companies}}",
                "period": "1d",  # Fixed to 1 day for speed
                "include_analysis": False
            },
            description="Quick financial data fetch"
        ),
        
        # Quick analysis
        LLMOperatorConfig(
            id="quick_analysis",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            prompt_template="""Quick market status for companies:

Companies: {{inputs.companies}}
Financial Data: {{quick_fetch.data}}

Generate:
1. Current market status (2-3 sentences)
2. Top price movements
3. Quick risk assessment
4. Simple buy/hold/sell recommendations""",
            dependencies=["quick_fetch"],
            temperature=0.3,
            description="Quick market analysis"
        )
    ]
    
    workflow = Workflow(
        nodes=nodes,
        name="simple_market_check",
        version="1.0.0"
    )
    
    return workflow


# Export workflows
__all__ = ["create_market_monitoring_workflow", "create_simple_market_check"] 