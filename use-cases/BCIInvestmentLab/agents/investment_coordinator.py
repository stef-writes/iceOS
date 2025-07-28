"""
🎯 Investment Coordinator Agent
==============================

Strategic coordination agent with recursive communication capabilities.

This agent specializes in:
- Synthesizing multi-agent research and market insights
- Recursive agent-to-agent communication until convergence
- Investment thesis development and validation
- Risk assessment and portfolio recommendations
- Strategic decision making with uncertainty handling

Memory Usage:
- **Strategic Memory**: High-level investment strategies and coordination patterns
- **Communication Logs**: Agent interaction history and consensus building
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pydantic import Field
import asyncio

from ice_orchestrator.agent.memory import MemoryAgent, MemoryAgentConfig
from ice_orchestrator.memory import UnifiedMemoryConfig, MemoryConfig
from ice_core.models.llm import LLMConfig
from ice_core.models.node_models import ToolConfig

# Import other agents for coordination
from .neuroscience_researcher import NeuroscienceResearcher, NeuroscienceResearcherConfig
from .market_intelligence import MarketIntelligenceAgent, MarketIntelligenceConfig


class InvestmentCoordinatorConfig(MemoryAgentConfig):
    """Configuration for the Investment Coordinator Agent."""
    
    type: str = "agent"
    package: str = "use_cases.BCIInvestmentLab.agents.investment_coordinator"
    agent_attr: str = "InvestmentCoordinator"
    
    # Strategic coordination memory configuration
    memory_config: UnifiedMemoryConfig = Field(
        default_factory=lambda: UnifiedMemoryConfig(
            enable_working=True,    # Track current coordination sessions
            enable_episodic=True,   # Store coordination sessions and decisions
            enable_semantic=False,  # Strategic agent doesn't need semantic facts
            enable_procedural=True, # Learn successful coordination patterns
            working_config=MemoryConfig(backend="memory", ttl_seconds=3600),  # 1 hour sessions
            episodic_config=MemoryConfig(backend="redis", ttl_seconds=86400 * 60),  # 60 days
            procedural_config=MemoryConfig(backend="file")  # Coordination strategies
        )
    )
    
    # Strategic LLM configuration
    llm_config: LLMConfig = Field(
        default_factory=lambda: LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            temperature=0.1,  # Very low for consistent strategic decisions
            max_tokens=4000
        )
    )
    
    # Coordination parameters
    max_coordination_rounds: int = Field(
        default=5,
        description="Maximum recursive communication rounds"
    )
    convergence_threshold: float = Field(
        default=0.85,
        description="Consensus threshold for convergence (0.0-1.0)"
    )
    decision_confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence required for investment decisions"
    )


class InvestmentCoordinator(MemoryAgent):
    """Strategic investment coordinator with recursive agent communication.
    
    This agent orchestrates multiple specialist agents to build comprehensive
    investment theses through iterative consensus building:
    
    1. **Research Synthesis**: Combines neuroscience research with market intelligence
    2. **Recursive Negotiation**: Iterates between agents until convergence
    3. **Risk Assessment**: Evaluates investment risks from multiple perspectives
    4. **Strategic Decisions**: Makes final investment recommendations
    
    Example usage:
    ```python
    coordinator = InvestmentCoordinator()
    result = await coordinator.execute({
        "investment_query": "BCI technology investment opportunity assessment",
        "time_horizon": "18_months",
        "risk_tolerance": "moderate",
        "investment_amount": 1000000
    })
    ```
    """
    
    config: InvestmentCoordinatorConfig
    
    def __init__(self, config: Optional[InvestmentCoordinatorConfig] = None):
        """Initialize the investment coordinator agent.
        
        Args:
            config: Agent configuration, uses defaults if None
        """
        if config is None:
            config = InvestmentCoordinatorConfig()
        super().__init__(config)
        
        # Initialize specialist agents
        self.research_agent = None
        self.market_agent = None
        
        # Investment focus areas
        self.investment_themes = [
            "early_stage_bci",
            "clinical_applications",
            "consumer_neurotechnology",
            "neural_prosthetics",
            "brain_therapeutics",
            "neurotech_platforms",
            "regulatory_pathway"
        ]
        
    async def _initialize_agents(self) -> None:
        """Initialize specialist agents for coordination."""
        if not self.research_agent:
            research_config = NeuroscienceResearcherConfig()
            self.research_agent = NeuroscienceResearcher(research_config)
            
        if not self.market_agent:
            market_config = MarketIntelligenceConfig()
            self.market_agent = MarketIntelligenceAgent(market_config)
            
    async def _execute_with_memory(self, enhanced_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute investment coordination with recursive agent communication.
        
        Args:
            enhanced_inputs: Inputs enhanced with memory context
            
        Returns:
            Comprehensive investment analysis and recommendations
        """
        investment_query = enhanced_inputs.get("investment_query", "")
        time_horizon = enhanced_inputs.get("time_horizon", "12_months")
        risk_tolerance = enhanced_inputs.get("risk_tolerance", "moderate")
        investment_amount = enhanced_inputs.get("investment_amount", 0)
        
        # Initialize specialist agents
        await self._initialize_agents()
        
        # Load coordination context from memory
        context = await self._load_coordination_context(investment_query)
        
        # Start recursive coordination process
        coordination_result = await self._coordinate_recursive_analysis(
            investment_query, time_horizon, risk_tolerance, context
        )
        
        # Synthesize final investment thesis
        investment_thesis = await self._synthesize_investment_thesis(
            coordination_result, investment_amount, risk_tolerance
        )
        
        # Generate strategic recommendations
        recommendations = await self._generate_strategic_recommendations(
            investment_thesis, coordination_result
        )
        
        # Store coordination session
        await self._store_coordination_session(
            investment_query, coordination_result, investment_thesis, recommendations
        )
        
        return {
            "status": "success",
            "investment_query": investment_query,
            "coordination_summary": {
                "rounds_completed": coordination_result.get("rounds_completed", 0),
                "convergence_achieved": coordination_result.get("convergence_achieved", False),
                "consensus_score": coordination_result.get("consensus_score", 0.0)
            },
            "research_insights": coordination_result.get("research_analysis", {}),
            "market_analysis": coordination_result.get("market_analysis", {}),
            "investment_thesis": investment_thesis,
            "strategic_recommendations": recommendations,
            "risk_assessment": investment_thesis.get("risk_assessment", {}),
            "confidence_score": investment_thesis.get("confidence_score", 0.0),
            "metadata": {
                "coordination_timestamp": datetime.now().isoformat(),
                "time_horizon": time_horizon,
                "risk_tolerance": risk_tolerance,
                "investment_amount": investment_amount,
                "themes_analyzed": self._identify_themes(investment_query)
            }
        }
        
    async def _load_coordination_context(self, investment_query: str) -> Dict[str, Any]:
        """Load coordination context from memory.
        
        Args:
            investment_query: Investment query to analyze
            
        Returns:
            Coordination context from memory
        """
        context = {}
        
        if self.memory:
            # Load past coordination sessions
            if self.memory.episodic:
                past_sessions = await self.memory.search_memory(
                    f"coordination {investment_query}",
                    memory_types=["episodic"],
                    limit=10
                )
                context["past_coordinations"] = past_sessions
                
            # Load successful coordination procedures
            if self.memory.procedural:
                coordination_methods = await self.memory.search_memory(
                    "successful coordination strategy",
                    memory_types=["procedural"],
                    limit=5
                )
                context["proven_strategies"] = coordination_methods
                
            # Load current working context
            if self.memory.working:
                current_session = await self.memory.working.retrieve("work:current_coordination")
                if current_session:
                    context["current_session"] = current_session.content
                    
        return context
        
    async def _coordinate_recursive_analysis(
        self, 
        investment_query: str, 
        time_horizon: str,
        risk_tolerance: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate recursive analysis between specialist agents.
        
        Args:
            investment_query: Investment query
            time_horizon: Investment time horizon
            risk_tolerance: Risk tolerance level
            context: Coordination context
            
        Returns:
            Coordination results with agent analyses and consensus
        """
        coordination_log = []
        research_analysis = None
        market_analysis = None
        consensus_score = 0.0
        
        for round_num in range(1, self.config.max_coordination_rounds + 1):
            round_start = datetime.now()
            
            # Research agent analysis (informed by previous market analysis if available)
            research_inputs = {
                "query": investment_query,
                "research_focus": self._extract_research_focus(investment_query),
                "time_horizon": time_horizon,
                "market_context": market_analysis if market_analysis else {}
            }
            
            research_analysis = await self.research_agent.execute(research_inputs)
            
            # Market agent analysis (informed by research findings)
            market_inputs = {
                "analysis_type": "investment_opportunity",
                "focus": self._extract_market_focus(investment_query),
                "time_range": self._map_time_horizon_to_range(time_horizon),
                "research_context": research_analysis
            }
            
            market_analysis = await self.market_agent.execute(market_inputs)
            
            # Calculate consensus between agents
            consensus_score = self._calculate_consensus(research_analysis, market_analysis)
            
            # Log this coordination round
            round_log = {
                "round": round_num,
                "research_confidence": research_analysis.get("metadata", {}).get("confidence_score", 0.5),
                "market_confidence": market_analysis.get("metadata", {}).get("confidence_score", 0.5),
                "consensus_score": consensus_score,
                "duration_seconds": (datetime.now() - round_start).total_seconds(),
                "convergence_factors": self._identify_convergence_factors(research_analysis, market_analysis)
            }
            coordination_log.append(round_log)
            
            # Store working memory for current round
            await self._store_round_progress(round_num, research_analysis, market_analysis, consensus_score)
            
            # Check for convergence
            if consensus_score >= self.config.convergence_threshold:
                break
                
            # Prepare feedback for next iteration
            await self._prepare_iteration_feedback(research_analysis, market_analysis, round_num)
            
        return {
            "rounds_completed": len(coordination_log),
            "convergence_achieved": consensus_score >= self.config.convergence_threshold,
            "consensus_score": consensus_score,
            "coordination_log": coordination_log,
            "research_analysis": research_analysis,
            "market_analysis": market_analysis,
            "final_synthesis": self._synthesize_agent_outputs(research_analysis, market_analysis)
        }
        
    def _calculate_consensus(
        self, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any]
    ) -> float:
        """Calculate consensus score between agent analyses.
        
        Args:
            research_analysis: Research agent results
            market_analysis: Market agent results
            
        Returns:
            Consensus score (0.0 to 1.0)
        """
        consensus_factors = []
        
        # Compare investment sentiment
        research_positive = self._extract_sentiment(research_analysis, "positive")
        market_positive = self._extract_sentiment(market_analysis, "positive")
        
        if research_positive and market_positive:
            consensus_factors.append(0.3)  # Both positive
        elif not research_positive and not market_positive:
            consensus_factors.append(0.3)  # Both negative
        else:
            consensus_factors.append(0.0)  # Conflicting
            
        # Compare confidence levels
        research_confidence = research_analysis.get("metadata", {}).get("confidence_score", 0.5)
        market_confidence = market_analysis.get("metadata", {}).get("confidence_score", 0.5)
        
        confidence_alignment = 1.0 - abs(research_confidence - market_confidence)
        consensus_factors.append(confidence_alignment * 0.2)
        
        # Compare risk assessments
        research_risks = len(research_analysis.get("research_insights", {}).get("technical_challenges", []))
        market_risks = len(market_analysis.get("risk_assessment", {}).get("risk_factors", []))
        
        if research_risks > 0 and market_risks > 0:
            risk_alignment = min(research_risks, market_risks) / max(research_risks, market_risks)
            consensus_factors.append(risk_alignment * 0.2)
        else:
            consensus_factors.append(0.1)
            
        # Check for supporting evidence
        research_recommendations = len(research_analysis.get("recommendations", []))
        market_recommendations = len(market_analysis.get("recommendations", []))
        
        if research_recommendations > 0 and market_recommendations > 0:
            consensus_factors.append(0.3)  # Both have recommendations
        else:
            consensus_factors.append(0.1)
            
        return sum(consensus_factors)
        
    def _extract_sentiment(self, analysis: Dict[str, Any], sentiment_type: str) -> bool:
        """Extract sentiment from agent analysis.
        
        Args:
            analysis: Agent analysis results
            sentiment_type: Type of sentiment to check for
            
        Returns:
            True if sentiment type found, False otherwise
        """
        analysis_str = str(analysis).lower()
        
        if sentiment_type == "positive":
            positive_indicators = ["buy", "bullish", "opportunity", "growth", "breakthrough"]
            return any(indicator in analysis_str for indicator in positive_indicators)
        elif sentiment_type == "negative":
            negative_indicators = ["sell", "bearish", "risk", "decline", "concern"]
            return any(indicator in analysis_str for indicator in negative_indicators)
            
        return False
        
    def _identify_convergence_factors(
        self, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any]
    ) -> List[str]:
        """Identify factors contributing to convergence or divergence.
        
        Args:
            research_analysis: Research agent results
            market_analysis: Market agent results
            
        Returns:
            List of convergence factors
        """
        factors = []
        
        # Check for aligned recommendations
        research_recs = research_analysis.get("recommendations", [])
        market_recs = market_analysis.get("recommendations", [])
        
        if research_recs and market_recs:
            factors.append("Both agents provide recommendations")
            
        # Check for consistent confidence
        research_conf = research_analysis.get("metadata", {}).get("confidence_score", 0.5)
        market_conf = market_analysis.get("metadata", {}).get("confidence_score", 0.5)
        
        if abs(research_conf - market_conf) < 0.2:
            factors.append("Consistent confidence levels")
        else:
            factors.append("Divergent confidence levels")
            
        # Check for risk alignment
        research_risks = research_analysis.get("research_insights", {}).get("technical_challenges", [])
        market_risks = market_analysis.get("risk_assessment", {}).get("risk_factors", [])
        
        if research_risks and market_risks:
            factors.append("Both identify risk factors")
        elif not research_risks and not market_risks:
            factors.append("Both see minimal risks")
        else:
            factors.append("Disagreement on risk assessment")
            
        return factors
        
    async def _store_round_progress(
        self, 
        round_num: int, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any],
        consensus_score: float
    ) -> None:
        """Store progress of current coordination round.
        
        Args:
            round_num: Current round number
            research_analysis: Research results
            market_analysis: Market results
            consensus_score: Current consensus score
        """
        if self.memory and self.memory.working:
            await self.memory.working.store(
                f"work:coordination_round_{round_num}",
                {
                    "round": round_num,
                    "research_summary": self._summarize_analysis(research_analysis),
                    "market_summary": self._summarize_analysis(market_analysis),
                    "consensus_score": consensus_score,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
    def _summarize_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize agent analysis for storage.
        
        Args:
            analysis: Full analysis results
            
        Returns:
            Summarized analysis
        """
        return {
            "status": analysis.get("status", "unknown"),
            "confidence": analysis.get("metadata", {}).get("confidence_score", 0.5),
            "key_points": analysis.get("recommendations", [])[:3],  # Top 3 recommendations
            "risk_factors": analysis.get("risk_assessment", {}).get("risk_factors", [])[:2]  # Top 2 risks
        }
        
    async def _prepare_iteration_feedback(
        self, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any],
        round_num: int
    ) -> None:
        """Prepare feedback for next iteration to improve convergence.
        
        Args:
            research_analysis: Current research results
            market_analysis: Current market results
            round_num: Current round number
        """
        # In a full implementation, this would provide feedback to agents
        # to help them adjust their analysis in subsequent rounds
        feedback = {
            "research_feedback": self._generate_research_feedback(market_analysis),
            "market_feedback": self._generate_market_feedback(research_analysis),
            "convergence_guidance": self._generate_convergence_guidance(research_analysis, market_analysis)
        }
        
        if self.memory and self.memory.working:
            await self.memory.working.store(
                f"work:iteration_feedback_{round_num}",
                feedback
            )
            
    def _generate_research_feedback(self, market_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feedback for research agent based on market analysis.
        
        Args:
            market_analysis: Market agent results
            
        Returns:
            Research feedback
        """
        return {
            "market_signals": market_analysis.get("investment_signals", []),
            "financial_trends": market_analysis.get("market_trends", []),
            "focus_companies": market_analysis.get("companies_analyzed", [])
        }
        
    def _generate_market_feedback(self, research_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feedback for market agent based on research analysis.
        
        Args:
            research_analysis: Research agent results
            
        Returns:
            Market feedback
        """
        return {
            "breakthrough_indicators": research_analysis.get("research_insights", {}).get("breakthrough_indicators", []),
            "technology_readiness": research_analysis.get("technology_readiness", {}),
            "research_gaps": research_analysis.get("research_insights", {}).get("research_gaps", [])
        }
        
    def _generate_convergence_guidance(
        self, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate guidance to improve convergence.
        
        Args:
            research_analysis: Research results
            market_analysis: Market results
            
        Returns:
            Convergence guidance
        """
        return {
            "alignment_opportunities": self._identify_alignment_opportunities(research_analysis, market_analysis),
            "divergence_issues": self._identify_divergence_issues(research_analysis, market_analysis),
            "focus_areas": self._suggest_focus_areas(research_analysis, market_analysis)
        }
        
    def _identify_alignment_opportunities(
        self, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any]
    ) -> List[str]:
        """Identify opportunities for agent alignment.
        
        Args:
            research_analysis: Research results
            market_analysis: Market results
            
        Returns:
            List of alignment opportunities
        """
        opportunities = []
        
        # Check for overlapping themes
        research_themes = research_analysis.get("research_insights", {}).get("emerging_trends", [])
        market_themes = market_analysis.get("market_trends", [])
        
        overlapping_themes = set(str(t).lower() for t in research_themes) & set(str(t).lower() for t in market_themes)
        if overlapping_themes:
            opportunities.append(f"Shared themes: {', '.join(overlapping_themes)}")
            
        return opportunities
        
    def _identify_divergence_issues(
        self, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any]
    ) -> List[str]:
        """Identify issues causing divergence.
        
        Args:
            research_analysis: Research results
            market_analysis: Market results
            
        Returns:
            List of divergence issues
        """
        issues = []
        
        # Check for conflicting recommendations
        research_recs = [str(r).lower() for r in research_analysis.get("recommendations", [])]
        market_recs = [str(r).lower() for r in market_analysis.get("recommendations", [])]
        
        research_positive = any("buy" in r or "invest" in r for r in research_recs)
        market_positive = any("buy" in r or "invest" in r for r in market_recs)
        
        if research_positive != market_positive:
            issues.append("Conflicting investment sentiment")
            
        return issues
        
    def _suggest_focus_areas(
        self, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any]
    ) -> List[str]:
        """Suggest focus areas for next iteration.
        
        Args:
            research_analysis: Research results
            market_analysis: Market results
            
        Returns:
            List of suggested focus areas
        """
        focus_areas = []
        
        # Suggest areas where more analysis is needed
        research_gaps = research_analysis.get("research_insights", {}).get("research_gaps", [])
        if research_gaps:
            focus_areas.append("Address research gaps identified")
            
        market_risks = market_analysis.get("risk_assessment", {}).get("risk_factors", [])
        if market_risks:
            focus_areas.append("Evaluate market risk factors")
            
        return focus_areas
        
    def _synthesize_agent_outputs(
        self, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize outputs from both agents.
        
        Args:
            research_analysis: Research agent results
            market_analysis: Market agent results
            
        Returns:
            Synthesized analysis
        """
        return {
            "combined_insights": {
                "research_breakthroughs": research_analysis.get("research_insights", {}).get("breakthrough_indicators", []),
                "market_opportunities": market_analysis.get("investment_signals", []),
                "technology_readiness": research_analysis.get("technology_readiness", {}),
                "financial_indicators": market_analysis.get("financial_summary", {})
            },
            "unified_recommendations": self._unify_recommendations(research_analysis, market_analysis),
            "comprehensive_risks": self._combine_risk_assessments(research_analysis, market_analysis)
        }
        
    def _unify_recommendations(
        self, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any]
    ) -> List[str]:
        """Unify recommendations from both agents.
        
        Args:
            research_analysis: Research results
            market_analysis: Market results
            
        Returns:
            Unified recommendations
        """
        unified = []
        
        research_recs = research_analysis.get("recommendations", [])
        market_recs = market_analysis.get("recommendations", [])
        
        # Combine and deduplicate recommendations
        all_recs = research_recs + market_recs
        seen = set()
        
        for rec in all_recs:
            rec_lower = str(rec).lower()
            if rec_lower not in seen:
                unified.append(rec)
                seen.add(rec_lower)
                
        return unified[:10]  # Limit to top 10
        
    def _combine_risk_assessments(
        self, 
        research_analysis: Dict[str, Any], 
        market_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine risk assessments from both agents.
        
        Args:
            research_analysis: Research results
            market_analysis: Market results
            
        Returns:
            Combined risk assessment
        """
        combined_risks = {
            "technical_risks": research_analysis.get("research_insights", {}).get("technical_challenges", []),
            "market_risks": market_analysis.get("risk_assessment", {}).get("risk_factors", []),
            "overall_risk_level": "medium"  # Default
        }
        
        # Calculate overall risk level
        total_risks = len(combined_risks["technical_risks"]) + len(combined_risks["market_risks"])
        
        if total_risks >= 5:
            combined_risks["overall_risk_level"] = "high"
        elif total_risks >= 2:
            combined_risks["overall_risk_level"] = "medium"
        else:
            combined_risks["overall_risk_level"] = "low"
            
        return combined_risks
        
    async def _synthesize_investment_thesis(
        self, 
        coordination_result: Dict[str, Any], 
        investment_amount: float,
        risk_tolerance: str
    ) -> Dict[str, Any]:
        """Synthesize final investment thesis from coordination results.
        
        Args:
            coordination_result: Results from recursive coordination
            investment_amount: Investment amount
            risk_tolerance: Risk tolerance level
            
        Returns:
            Investment thesis
        """
        thesis = {
            "investment_opportunity": self._evaluate_investment_opportunity(coordination_result),
            "strategic_rationale": self._develop_strategic_rationale(coordination_result),
            "risk_assessment": coordination_result.get("final_synthesis", {}).get("comprehensive_risks", {}),
            "financial_projections": self._generate_financial_projections(coordination_result, investment_amount),
            "implementation_timeline": self._create_implementation_timeline(coordination_result),
            "success_metrics": self._define_success_metrics(coordination_result),
            "confidence_score": self._calculate_thesis_confidence(coordination_result, risk_tolerance)
        }
        
        return thesis
        
    def _evaluate_investment_opportunity(self, coordination_result: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the investment opportunity.
        
        Args:
            coordination_result: Coordination results
            
        Returns:
            Investment opportunity evaluation
        """
        convergence_achieved = coordination_result.get("convergence_achieved", False)
        consensus_score = coordination_result.get("consensus_score", 0.0)
        
        if convergence_achieved and consensus_score >= 0.8:
            opportunity_rating = "high"
        elif consensus_score >= 0.6:
            opportunity_rating = "medium"
        else:
            opportunity_rating = "low"
            
        return {
            "rating": opportunity_rating,
            "consensus_score": consensus_score,
            "convergence_achieved": convergence_achieved,
            "key_factors": coordination_result.get("final_synthesis", {}).get("combined_insights", {})
        }
        
    def _develop_strategic_rationale(self, coordination_result: Dict[str, Any]) -> Dict[str, Any]:
        """Develop strategic rationale for investment.
        
        Args:
            coordination_result: Coordination results
            
        Returns:
            Strategic rationale
        """
        combined_insights = coordination_result.get("final_synthesis", {}).get("combined_insights", {})
        
        return {
            "technology_thesis": combined_insights.get("research_breakthroughs", []),
            "market_thesis": combined_insights.get("market_opportunities", []),
            "competitive_advantages": self._identify_competitive_advantages(combined_insights),
            "growth_drivers": self._identify_growth_drivers(combined_insights)
        }
        
    def _identify_competitive_advantages(self, insights: Dict[str, Any]) -> List[str]:
        """Identify competitive advantages from insights.
        
        Args:
            insights: Combined insights
            
        Returns:
            List of competitive advantages
        """
        advantages = []
        
        breakthroughs = insights.get("research_breakthroughs", [])
        if breakthroughs:
            advantages.append("Technology breakthrough potential")
            
        tech_readiness = insights.get("technology_readiness", {})
        if tech_readiness.get("readiness_level", 0) >= 6:
            advantages.append("Advanced technology readiness")
            
        return advantages
        
    def _identify_growth_drivers(self, insights: Dict[str, Any]) -> List[str]:
        """Identify growth drivers from insights.
        
        Args:
            insights: Combined insights
            
        Returns:
            List of growth drivers
        """
        drivers = []
        
        market_opportunities = insights.get("market_opportunities", [])
        if market_opportunities:
            drivers.append("Strong market signals")
            
        financial_indicators = insights.get("financial_indicators", {})
        if financial_indicators.get("average_performance", 0) > 0:
            drivers.append("Positive financial trends")
            
        return drivers
        
    def _generate_financial_projections(
        self, 
        coordination_result: Dict[str, Any], 
        investment_amount: float
    ) -> Dict[str, Any]:
        """Generate financial projections for investment.
        
        Args:
            coordination_result: Coordination results
            investment_amount: Investment amount
            
        Returns:
            Financial projections
        """
        # Simple projections based on consensus and market data
        consensus_score = coordination_result.get("consensus_score", 0.5)
        
        projected_return = investment_amount * (0.1 + (consensus_score * 0.3))  # 10-40% based on consensus
        
        return {
            "initial_investment": investment_amount,
            "projected_return_1y": projected_return,
            "projected_roi": (projected_return - investment_amount) / investment_amount if investment_amount > 0 else 0,
            "payback_period_months": 24 if consensus_score > 0.7 else 36,
            "risk_adjusted_return": projected_return * consensus_score
        }
        
    def _create_implementation_timeline(self, coordination_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create implementation timeline.
        
        Args:
            coordination_result: Coordination results
            
        Returns:
            Implementation timeline
        """
        convergence_achieved = coordination_result.get("convergence_achieved", False)
        
        if convergence_achieved:
            timeline = {
                "phase_1_due_diligence": "1-2 months",
                "phase_2_initial_investment": "3-4 months", 
                "phase_3_monitoring": "6-12 months",
                "phase_4_follow_on": "12-18 months"
            }
        else:
            timeline = {
                "phase_1_additional_analysis": "2-3 months",
                "phase_2_re_evaluation": "4-5 months",
                "phase_3_decision": "6 months"
            }
            
        return timeline
        
    def _define_success_metrics(self, coordination_result: Dict[str, Any]) -> List[str]:
        """Define success metrics for investment.
        
        Args:
            coordination_result: Coordination results
            
        Returns:
            List of success metrics
        """
        metrics = [
            "Technology milestone achievements",
            "Market penetration rates",
            "Revenue growth trajectory",
            "Competitive position strength"
        ]
        
        # Add specific metrics based on coordination results
        research_analysis = coordination_result.get("research_analysis", {})
        if research_analysis.get("technology_readiness", {}).get("readiness_level", 0) >= 6:
            metrics.append("Clinical trial progression")
            
        market_analysis = coordination_result.get("market_analysis", {})
        if market_analysis.get("investment_signals"):
            metrics.append("Market signal validation")
            
        return metrics
        
    def _calculate_thesis_confidence(
        self, 
        coordination_result: Dict[str, Any], 
        risk_tolerance: str
    ) -> float:
        """Calculate confidence score for investment thesis.
        
        Args:
            coordination_result: Coordination results
            risk_tolerance: Risk tolerance level
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        base_confidence = coordination_result.get("consensus_score", 0.5)
        
        # Adjust based on convergence
        if coordination_result.get("convergence_achieved", False):
            base_confidence += 0.1
            
        # Adjust based on risk tolerance
        risk_adjustment = {
            "low": -0.1,
            "moderate": 0.0,
            "high": 0.1
        }.get(risk_tolerance, 0.0)
        
        return min(base_confidence + risk_adjustment, 1.0)
        
    async def _generate_strategic_recommendations(
        self, 
        investment_thesis: Dict[str, Any], 
        coordination_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate strategic recommendations.
        
        Args:
            investment_thesis: Investment thesis
            coordination_result: Coordination results
            
        Returns:
            List of strategic recommendations
        """
        recommendations = []
        
        confidence_score = investment_thesis.get("confidence_score", 0.0)
        
        if confidence_score >= self.config.decision_confidence_threshold:
            recommendations.append({
                "type": "investment_decision",
                "action": "proceed",
                "rationale": "High confidence in investment thesis",
                "priority": "high"
            })
        else:
            recommendations.append({
                "type": "investment_decision",
                "action": "additional_analysis",
                "rationale": "Confidence below threshold, require more analysis",
                "priority": "medium"
            })
            
        # Add specific recommendations based on analysis
        risk_level = investment_thesis.get("risk_assessment", {}).get("overall_risk_level", "medium")
        
        if risk_level == "high":
            recommendations.append({
                "type": "risk_management",
                "action": "implement_risk_controls",
                "rationale": "High risk level requires additional controls",
                "priority": "high"
            })
            
        return recommendations
        
    async def _store_coordination_session(
        self,
        investment_query: str,
        coordination_result: Dict[str, Any],
        investment_thesis: Dict[str, Any],
        recommendations: List[Dict[str, Any]]
    ) -> None:
        """Store coordination session in memory.
        
        Args:
            investment_query: Original investment query
            coordination_result: Coordination results
            investment_thesis: Final investment thesis
            recommendations: Strategic recommendations
        """
        if not self.memory:
            return
            
        timestamp = datetime.now().isoformat()
        
        # Store in episodic memory
        if self.memory.episodic:
            await self.memory.episodic.store(
                f"episode:coordination_session:{timestamp}",
                {
                    "investment_query": investment_query,
                    "convergence_achieved": coordination_result.get("convergence_achieved", False),
                    "consensus_score": coordination_result.get("consensus_score", 0.0),
                    "confidence_score": investment_thesis.get("confidence_score", 0.0),
                    "decision_made": len([r for r in recommendations if r["action"] == "proceed"]) > 0,
                    "timestamp": timestamp
                },
                metadata={"type": "coordination_session", "query": investment_query}
            )
            
        # Store successful coordination procedures
        if self.memory.procedural:
            if coordination_result.get("convergence_achieved", False):
                await self.memory.procedural.store(
                    f"procedure:successful_coordination:{hash(investment_query)}",
                    {
                        "coordination_strategy": "recursive_agent_communication",
                        "rounds_to_convergence": coordination_result.get("rounds_completed", 0),
                        "success_factors": coordination_result.get("coordination_log", [])[-1] if coordination_result.get("coordination_log") else {},
                        "timestamp": timestamp
                    },
                    metadata={"type": "successful_coordination"}
                )
                
    def _extract_research_focus(self, investment_query: str) -> str:
        """Extract research focus from investment query.
        
        Args:
            investment_query: Investment query string
            
        Returns:
            Research focus area
        """
        query_lower = investment_query.lower()
        
        for theme in self.investment_themes:
            if theme.replace("_", " ") in query_lower:
                return theme
                
        return "general_bci_research"
        
    def _extract_market_focus(self, investment_query: str) -> str:
        """Extract market focus from investment query.
        
        Args:
            investment_query: Investment query string
            
        Returns:
            Market focus area
        """
        query_lower = investment_query.lower()
        
        if "neurotechnology" in query_lower or "bci" in query_lower:
            return "neurotechnology"
        elif "healthcare" in query_lower or "medical" in query_lower:
            return "healthcare"
        elif "consumer" in query_lower:
            return "consumer_technology"
        else:
            return "technology"
            
    def _map_time_horizon_to_range(self, time_horizon: str) -> str:
        """Map investment time horizon to market analysis range.
        
        Args:
            time_horizon: Investment time horizon
            
        Returns:
            Market analysis time range
        """
        horizon_map = {
            "6_months": "90_days",
            "12_months": "1_year",
            "18_months": "1_year",
            "24_months": "1_year",
            "3_years": "1_year"
        }
        
        return horizon_map.get(time_horizon, "1_year")
        
    def _identify_themes(self, investment_query: str) -> List[str]:
        """Identify investment themes from query.
        
        Args:
            investment_query: Investment query
            
        Returns:
            List of relevant themes
        """
        query_lower = investment_query.lower()
        relevant_themes = []
        
        for theme in self.investment_themes:
            theme_words = theme.replace("_", " ").split()
            if any(word in query_lower for word in theme_words):
                relevant_themes.append(theme)
                
        return relevant_themes if relevant_themes else ["general_investment"]


# Export for registration
__all__ = ["InvestmentCoordinator", "InvestmentCoordinatorConfig"] 