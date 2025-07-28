"""
🧠 Neuroscience Researcher Agent
==============================

Expert agent for BCI research analysis with comprehensive memory capabilities.

This agent specializes in:
- Academic literature analysis and synthesis
- Technology readiness assessment
- Research breakthrough tracking
- Statistical pattern recognition
- Long-term research trend analysis

Memory Usage:
- **Working Memory**: Current research session context, active queries
- **Episodic Memory**: Research sessions, breakthrough discoveries, paper reviews
- **Semantic Memory**: Research facts, scientific knowledge, technology mappings
- **Procedural Memory**: Research methodologies, analysis patterns, evaluation criteria
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pydantic import Field

from ice_orchestrator.agent.memory import MemoryAgent, MemoryAgentConfig
from ice_orchestrator.memory import UnifiedMemoryConfig, MemoryConfig
from ice_core.models.llm import LLMConfig
from ice_core.models.node_models import ToolConfig

# Import available tools
from use_cases.BCIInvestmentLab.tools import (
    ArxivSearchTool,
    StatisticalAnalyzerTool,
    TechnologyReadinessTool,
    NeuralSimulatorTool
)


class NeuroscienceResearcherConfig(MemoryAgentConfig):
    """Configuration for the Neuroscience Researcher Agent."""
    
    type: str = "agent"
    package: str = "use_cases.BCIInvestmentLab.agents.neuroscience_researcher"
    agent_attr: str = "NeuroscienceResearcher"
    
    # Specialized memory configuration for research
    memory_config: UnifiedMemoryConfig = Field(
        default_factory=lambda: UnifiedMemoryConfig(
            enable_working=True,
            enable_episodic=True, 
            enable_semantic=True,
            enable_procedural=True,
            working_config=MemoryConfig(backend="memory", ttl_seconds=1800),  # 30 min sessions
            episodic_config=MemoryConfig(backend="redis", ttl_seconds=86400 * 30),  # 30 days
            semantic_config=MemoryConfig(backend="sqlite"),  # Persistent knowledge
            procedural_config=MemoryConfig(backend="file")  # Research methods
        )
    )
    
    # Research-focused LLM configuration
    llm_config: LLMConfig = Field(
        default_factory=lambda: LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,  # Lower for more analytical responses
            max_tokens=4000
        )
    )
    
    # Available tools for research
    tools: List[ToolConfig] = Field(
        default_factory=lambda: [
            ToolConfig(name="arxiv_search", package="use_cases.BCIInvestmentLab.tools.arxiv_search"),
            ToolConfig(name="statistical_analyzer", package="use_cases.BCIInvestmentLab.tools.statistical_analyzer"),
            ToolConfig(name="technology_readiness", package="use_cases.BCIInvestmentLab.tools.technology_readiness"),
            ToolConfig(name="neural_simulator", package="use_cases.BCIInvestmentLab.tools.neural_simulator")
        ]
    )


class NeuroscienceResearcher(MemoryAgent):
    """Expert neuroscience research agent with comprehensive memory.
    
    This agent maintains deep understanding of BCI research through:
    - Continuous academic literature monitoring
    - Technology maturity assessment
    - Research pattern recognition
    - Scientific breakthrough tracking
    
    Example usage:
    ```python
    researcher = NeuroscienceResearcher()
    result = await researcher.execute({
        "query": "Latest breakthroughs in motor imagery BCI",
        "research_focus": "clinical_applications",
        "time_horizon": "6_months"
    })
    ```
    """
    
    config: NeuroscienceResearcherConfig
    
    def __init__(self, config: Optional[NeuroscienceResearcherConfig] = None):
        """Initialize the neuroscience researcher agent.
        
        Args:
            config: Agent configuration, uses defaults if None
        """
        if config is None:
            config = NeuroscienceResearcherConfig()
        super().__init__(config)
        
        # Research specialization areas
        self.research_domains = [
            "motor_imagery_bci",
            "visual_evoked_potentials", 
            "steady_state_bci",
            "invasive_bci",
            "non_invasive_bci",
            "neural_decoding",
            "brain_computer_interfaces",
            "neurofeedback",
            "neural_prosthetics"
        ]
        
    async def _execute_with_memory(self, enhanced_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute research analysis with memory-enhanced context.
        
        Args:
            enhanced_inputs: Inputs enhanced with memory context
            
        Returns:
            Research analysis results with discoveries and insights
        """
        query = enhanced_inputs.get("query", "")
        research_focus = enhanced_inputs.get("research_focus", "general")
        time_horizon = enhanced_inputs.get("time_horizon", "recent")
        
        # Load research context from memory
        context = await self._load_research_context(query, research_focus)
        
        # Perform academic search
        papers = await self._search_literature(query, time_horizon)
        
        # Analyze findings
        analysis = await self._analyze_research_findings(papers, context)
        
        # Assess technology readiness
        tech_assessment = await self._assess_technology_readiness(papers, research_focus)
        
        # Generate insights and recommendations
        insights = await self._generate_research_insights(analysis, tech_assessment, context)
        
        # Store research session in memory
        await self._store_research_session(query, papers, analysis, insights)
        
        return {
            "status": "success",
            "research_query": query,
            "papers_found": len(papers),
            "key_findings": analysis.get("key_findings", []),
            "technology_readiness": tech_assessment,
            "research_insights": insights,
            "recommendations": await self._generate_recommendations(insights),
            "metadata": {
                "research_focus": research_focus,
                "time_horizon": time_horizon,
                "analysis_timestamp": datetime.now().isoformat(),
                "domains_covered": self._identify_research_domains(papers)
            }
        }
        
    async def _load_research_context(self, query: str, focus: str) -> Dict[str, Any]:
        """Load relevant research context from memory.
        
        Args:
            query: Research query
            focus: Research focus area
            
        Returns:
            Research context from memory
        """
        context = {}
        
        if self.memory:
            # Load relevant semantic knowledge
            if self.memory.semantic:
                related_facts = await self.memory.search_memory(
                    f"{query} {focus}",
                    memory_types=["semantic"],
                    limit=20
                )
                context["known_facts"] = related_facts
                
            # Load research procedures
            if self.memory.procedural:
                research_methods = await self.memory.search_memory(
                    f"research methodology {focus}",
                    memory_types=["procedural"],
                    limit=10
                )
                context["research_methods"] = research_methods
                
            # Load past episodes
            if self.memory.episodic:
                past_research = await self.memory.search_memory(
                    query,
                    memory_types=["episodic"],
                    limit=5
                )
                context["past_research"] = past_research
                
        return context
        
    async def _search_literature(self, query: str, time_horizon: str) -> List[Dict[str, Any]]:
        """Search academic literature using ArxivSearchTool.
        
        Args:
            query: Research query
            time_horizon: Time range for search
            
        Returns:
            List of relevant papers
        """
        try:
            arxiv_tool = ArxivSearchTool()
            
            # Map time horizon to search parameters
            date_filter = {
                "recent": "last_month",
                "3_months": "last_3_months", 
                "6_months": "last_6_months",
                "1_year": "last_year",
                "all": None
            }.get(time_horizon, "recent")
            
            result = await arxiv_tool.execute({
                "query": query,
                "max_results": 50,
                "date_filter": date_filter,
                "sort_by": "relevance"
            })
            
            return result.get("papers", [])
            
        except Exception as e:
            # Fall back to empty list if search fails
            await self._log_error("literature_search", str(e))
            return []
            
    async def _analyze_research_findings(
        self, 
        papers: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze research findings using statistical analysis.
        
        Args:
            papers: List of research papers
            context: Research context from memory
            
        Returns:
            Analysis results with patterns and trends
        """
        try:
            if not papers:
                return {"key_findings": [], "trends": [], "patterns": []}
                
            stat_tool = StatisticalAnalyzerTool()
            
            # Extract relevant data for analysis
            paper_data = []
            for paper in papers:
                paper_data.append({
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "publication_date": paper.get("publication_date", ""),
                    "authors": paper.get("authors", []),
                    "categories": paper.get("categories", [])
                })
                
            result = await stat_tool.execute({
                "data": paper_data,
                "analysis_type": "research_trends",
                "focus_areas": self.research_domains
            })
            
            return result.get("analysis", {})
            
        except Exception as e:
            await self._log_error("research_analysis", str(e))
            return {"key_findings": [], "trends": [], "patterns": []}
            
    async def _assess_technology_readiness(
        self, 
        papers: List[Dict[str, Any]], 
        focus: str
    ) -> Dict[str, Any]:
        """Assess technology readiness levels from research.
        
        Args:
            papers: Research papers to analyze
            focus: Research focus area
            
        Returns:
            Technology readiness assessment
        """
        try:
            if not papers:
                return {"readiness_level": 1, "assessment": "insufficient_data"}
                
            tech_tool = TechnologyReadinessTool()
            
            # Prepare technology data from papers
            tech_data = {
                "technology_name": focus,
                "research_papers": papers[:10],  # Limit for analysis
                "focus_area": focus,
                "evaluation_criteria": [
                    "research_maturity",
                    "clinical_validation", 
                    "commercial_viability",
                    "regulatory_approval",
                    "market_readiness"
                ]
            }
            
            result = await tech_tool.execute(tech_data)
            return result.get("assessment", {})
            
        except Exception as e:
            await self._log_error("technology_assessment", str(e))
            return {"readiness_level": 1, "assessment": "analysis_failed"}
            
    async def _generate_research_insights(
        self,
        analysis: Dict[str, Any],
        tech_assessment: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate research insights by synthesizing all findings.
        
        Args:
            analysis: Statistical analysis results
            tech_assessment: Technology readiness assessment
            context: Memory context
            
        Returns:
            Research insights and synthesis
        """
        insights = {
            "breakthrough_indicators": [],
            "research_gaps": [],
            "emerging_trends": [],
            "investment_implications": [],
            "technical_challenges": [],
            "market_opportunities": []
        }
        
        # Extract breakthrough indicators
        key_findings = analysis.get("key_findings", [])
        for finding in key_findings:
            if self._is_breakthrough_indicator(finding):
                insights["breakthrough_indicators"].append(finding)
                
        # Identify research gaps
        known_facts = context.get("known_facts", [])
        current_trends = analysis.get("trends", [])
        insights["research_gaps"] = self._identify_research_gaps(known_facts, current_trends)
        
        # Extract emerging trends
        insights["emerging_trends"] = analysis.get("trends", [])[:5]
        
        # Assess investment implications
        readiness_level = tech_assessment.get("readiness_level", 1)
        insights["investment_implications"] = self._assess_investment_implications(
            readiness_level, 
            insights["breakthrough_indicators"]
        )
        
        return insights
        
    async def _store_research_session(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        analysis: Dict[str, Any], 
        insights: Dict[str, Any]
    ) -> None:
        """Store research session results in memory.
        
        Args:
            query: Original research query
            papers: Found papers
            analysis: Analysis results
            insights: Generated insights
        """
        if not self.memory:
            return
            
        timestamp = datetime.now().isoformat()
        
        # Store in episodic memory
        if self.memory.episodic:
            await self.memory.episodic.store(
                f"episode:research_session:{timestamp}",
                {
                    "query": query,
                    "papers_count": len(papers),
                    "key_findings": analysis.get("key_findings", []),
                    "insights": insights,
                    "timestamp": timestamp
                },
                metadata={"type": "research_session", "query": query}
            )
            
        # Store facts in semantic memory
        if self.memory.semantic:
            for finding in analysis.get("key_findings", []):
                await self.memory.semantic.store(
                    f"fact:research_finding:{hash(str(finding))}",
                    finding,
                    metadata={"source": "research_analysis", "timestamp": timestamp}
                )
                
        # Store successful procedures
        if self.memory.procedural:
            if len(papers) > 10:  # Consider successful if found many papers
                await self.memory.procedural.store(
                    f"procedure:successful_query:{hash(query)}",
                    {
                        "query_pattern": query,
                        "success_metrics": {"papers_found": len(papers)},
                        "timestamp": timestamp
                    },
                    metadata={"type": "successful_research_method"}
                )
                
    def _is_breakthrough_indicator(self, finding: Any) -> bool:
        """Determine if a finding indicates a potential breakthrough.
        
        Args:
            finding: Research finding to evaluate
            
        Returns:
            True if finding indicates breakthrough potential
        """
        finding_str = str(finding).lower()
        breakthrough_keywords = [
            "breakthrough", "novel", "unprecedented", "first", "significant improvement",
            "major advance", "paradigm shift", "revolutionary", "game-changing"
        ]
        return any(keyword in finding_str for keyword in breakthrough_keywords)
        
    def _identify_research_domains(self, papers: List[Dict[str, Any]]) -> List[str]:
        """Identify research domains covered by papers.
        
        Args:
            papers: List of research papers
            
        Returns:
            List of research domains found
        """
        found_domains = []
        for paper in papers:
            title = paper.get("title", "").lower()
            abstract = paper.get("abstract", "").lower()
            text = f"{title} {abstract}"
            
            for domain in self.research_domains:
                domain_keywords = domain.replace("_", " ").split()
                if all(keyword in text for keyword in domain_keywords):
                    if domain not in found_domains:
                        found_domains.append(domain)
                        
        return found_domains
        
    def _identify_research_gaps(
        self, 
        known_facts: List[Any], 
        current_trends: List[Any]
    ) -> List[str]:
        """Identify gaps between known knowledge and current research.
        
        Args:
            known_facts: Facts from semantic memory
            current_trends: Current research trends
            
        Returns:
            List of identified research gaps
        """
        # Simple gap analysis - could be enhanced with NLP
        gaps = []
        
        # Check for missing connections between domains
        covered_domains = set()
        for fact in known_facts:
            fact_str = str(fact).lower()
            for domain in self.research_domains:
                if domain.replace("_", " ") in fact_str:
                    covered_domains.add(domain)
                    
        uncovered_domains = set(self.research_domains) - covered_domains
        gaps.extend([f"Limited research in {domain}" for domain in uncovered_domains])
        
        return gaps[:5]  # Limit to top 5 gaps
        
    def _assess_investment_implications(
        self, 
        readiness_level: int, 
        breakthroughs: List[Any]
    ) -> List[str]:
        """Assess investment implications from research findings.
        
        Args:
            readiness_level: Technology readiness level (1-9)
            breakthroughs: List of breakthrough indicators
            
        Returns:
            List of investment implications
        """
        implications = []
        
        if readiness_level >= 7:
            implications.append("Technology approaching market readiness")
        elif readiness_level >= 4:
            implications.append("Technology in development phase, medium-term opportunity")
        else:
            implications.append("Early-stage research, long-term opportunity")
            
        if len(breakthroughs) > 2:
            implications.append("Multiple breakthrough indicators suggest accelerating progress")
        elif len(breakthroughs) > 0:
            implications.append("Breakthrough potential identified")
            
        return implications
        
    async def _generate_recommendations(self, insights: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations from insights.
        
        Args:
            insights: Research insights
            
        Returns:
            List of actionable recommendations
        """
        recommendations = []
        
        breakthrough_count = len(insights.get("breakthrough_indicators", []))
        if breakthrough_count > 0:
            recommendations.append(f"Monitor {breakthrough_count} breakthrough indicators closely")
            
        gaps = insights.get("research_gaps", [])
        if gaps:
            recommendations.append(f"Consider funding research in {len(gaps)} identified gap areas")
            
        trends = insights.get("emerging_trends", [])
        if trends:
            recommendations.append(f"Track {len(trends)} emerging research trends")
            
        opportunities = insights.get("market_opportunities", [])
        if opportunities:
            recommendations.append("Evaluate market opportunities in identified areas")
            
        return recommendations
        
    async def _log_error(self, operation: str, error: str) -> None:
        """Log errors for debugging.
        
        Args:
            operation: Operation that failed
            error: Error message
        """
        if self.memory and self.memory.working:
            await self.memory.working.store(
                f"work:error:{operation}",
                {
                    "operation": operation,
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                }
            )


# Export for registration
__all__ = ["NeuroscienceResearcher", "NeuroscienceResearcherConfig"] 