"""Market Monitoring Blueprint - Multi-Node Type Implementation"""

from ice_core.models.mcp import Blueprint, NodeSpec


def create_market_monitoring_blueprint(companies: list = None) -> Blueprint:
    """Market monitoring with comprehensive node type demonstration.
    
    Node types used: condition, parallel, tool, agent, llm
    """
    
    if companies is None:
        companies = ["NFLX", "META", "GOOGL", "NVDA"]
    
    return Blueprint(
        blueprint_id=f"market_monitoring_{len(companies)}_{hash(str(companies)) % 10000}",
        nodes=[
            # 1. CONDITION: Validate market hours
            NodeSpec(
                id="market_hours_check",
                type="condition",
                expression="true",  # Simplified for demo
                true_branch=["parallel_data_fetch"],
                false_branch=["market_closed_handler"],
                input_schema={"timestamp": "string"},
                output_schema={"condition_result": "boolean"}
            ),
            
            # 2. LLM: Market closed handler
            NodeSpec(
                id="market_closed_handler",
                type="llm",
                model="gpt-4o",
                prompt="Markets are closed. Provide analysis based on last available data and pre-market indicators.",
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4o", 
                    "temperature": 0.6,
                    "max_tokens": 400
                }
            ),
            
            # 3a. TOOL: Financial data
            NodeSpec(
                id="financial_data",
                type="tool",
                tool_name="yahoo_finance_fetcher",
                tool_args={
                    "symbols": companies,
                    "period": "1mo", 
                    "include_news": True
                }
            ),
            
            # 3b. TOOL: Sentiment data
            NodeSpec(
                id="sentiment_data",
                type="tool",
                tool_name="newsapi_sentiment", 
                tool_args={
                    "keywords": "brain computer interface neurotechnology",
                    "language": "en"
                }
            ),
            
            # 3c. TOOL: Company research
            NodeSpec(
                id="company_research",
                type="tool",
                tool_name="company_research",
                tool_args={
                    "companies": companies,
                    "research_depth": "comprehensive"
                }
            ),
            
            # 3d. PARALLEL: Execute data fetching concurrently 
            NodeSpec(
                id="parallel_data_fetch",
                type="parallel",
                dependencies=["market_hours_check"],
                branches=[
                    ["financial_data"],
                    ["sentiment_data"], 
                    ["company_research"]
                ],
                max_concurrency=3
            ),
            
            # 4. CONDITION: Data quality check
            NodeSpec(
                id="data_quality_check",
                type="condition", 
                dependencies=["parallel_data_fetch"],
                expression="len(parallel_data_fetch.financial_data) > 0 and len(parallel_data_fetch.sentiment_data) > 0",
                true_branch=["market_intelligence"],
                false_branch=["data_error_handler"],
                input_schema={"parallel_data_fetch": "object"},
                output_schema={"condition_result": "boolean"}
            ),
            
            # 5. LLM: Data error handler
            NodeSpec(
                id="data_error_handler",
                type="llm",
                model="gpt-4o",
                prompt="Insufficient data retrieved. Provide analysis based on available information and suggest alternative data sources.",
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            ),
            
            # 6. AGENT: Market intelligence analysis
            NodeSpec(
                id="market_intelligence",
                type="agent",
                package="market_intelligence",
                dependencies=["data_quality_check"],
                agent_config={
                    "analysis_focus": "BCI market trends",
                    "risk_assessment": True,
                    "companies": companies,
                    "memory_enabled": True
                },
                input_schema={"financial_data": "object", "sentiment_data": "object", "company_research": "object"},
                output_schema={"analysis": "object", "recommendations": "array"}
            ),
            
            # 7. LLM: Investment synthesis
            NodeSpec(
                id="investment_synthesis",
                type="llm",
                model="gpt-4o",
                dependencies=["market_intelligence"],
                prompt="""Generate investment brief for BCI market opportunities.

Financial Data: {{parallel_data_fetch.financial_data}}
Sentiment Analysis: {{parallel_data_fetch.sentiment_data}}
Company Research: {{parallel_data_fetch.company_research}}
Market Intelligence: {{market_intelligence.analysis}}

Provide executive investment brief covering:
1. Market sentiment and price movements
2. Key catalysts and risk factors
3. Company-specific opportunities
4. Investment recommendations
5. Risk/reward assessment""",
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4o",
                    "temperature": 0.6,
                    "max_tokens": 800
                }
            )
        ],
        metadata={
            "workflow_type": "market_monitoring",
            "companies_tracked": companies,
            "node_types_used": ["condition", "parallel", "tool", "agent", "llm"],
            "estimated_duration": "2-3 minutes",
            "real_time": True
        }
    ) 