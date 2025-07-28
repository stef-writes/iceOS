"""
🔬 TechnologyReadinessTool - Technology Maturity Assessment
=========================================================

Highly reusable tool for assessing technology readiness levels and maturity.
Perfect for any emerging technology assessment use case.

## Reusability
✅ Any emerging technology assessment
✅ Innovation pipeline analysis
✅ Investment due diligence
✅ R&D portfolio management
✅ Market entry timing decisions

## Features
- Technology Readiness Level (TRL) assessment
- Market readiness analysis
- Risk factor evaluation
- Commercial viability scoring
- Timeline predictions
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import math

from ice_sdk.tools.base import ToolBase
import structlog

logger = structlog.get_logger(__name__)


class TechnologyReadinessTool(ToolBase):
    """Assess technology readiness levels and market maturity.
    
    This tool evaluates technologies across multiple dimensions including
    technical maturity, market readiness, regulatory status, and commercial viability.
    """
    
    name: str = "technology_readiness"
    description: str = "Assess technology readiness levels and market maturity"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Execute technology readiness assessment.
        
        Args:
            technology_name: Name of technology to assess (required)
            domain: Technology domain (e.g., 'AI', 'biotech', 'fintech') (required)
            research_data: Research and development indicators (optional)
            market_data: Market and adoption indicators (optional)
            regulatory_data: Regulatory and compliance indicators (optional)
            assessment_criteria: Custom assessment criteria (default: standard TRL)
            include_timeline: Whether to include market timeline prediction (default: True)
            
        Returns:
            Dict containing comprehensive technology readiness assessment
        """
        try:
            # Extract and validate parameters
            technology_name = kwargs.get("technology_name")
            domain = kwargs.get("domain")
            
            if not technology_name:
                raise ValueError("Technology name is required")
            if not domain:
                raise ValueError("Technology domain is required")
            
            research_data = kwargs.get("research_data", {})
            market_data = kwargs.get("market_data", {})
            regulatory_data = kwargs.get("regulatory_data", {})
            assessment_criteria = kwargs.get("assessment_criteria", "standard")
            include_timeline = kwargs.get("include_timeline", True)
            
            logger.info(f"Assessing technology readiness for: {technology_name} in {domain}")
            
            # Perform multi-dimensional assessment
            trl_assessment = self._assess_technology_readiness_level(research_data, domain)
            market_readiness = self._assess_market_readiness(market_data, domain)
            regulatory_assessment = self._assess_regulatory_readiness(regulatory_data, domain)
            commercial_viability = self._assess_commercial_viability(research_data, market_data, domain)
            
            # Calculate overall readiness score
            overall_score = self._calculate_overall_readiness(
                trl_assessment, market_readiness, regulatory_assessment, commercial_viability
            )
            
            # Generate risk assessment
            risk_analysis = self._analyze_risks(research_data, market_data, regulatory_data, domain)
            
            # Predict timeline if requested
            timeline_prediction = {}
            if include_timeline:
                timeline_prediction = self._predict_market_timeline(
                    trl_assessment, market_readiness, regulatory_assessment, domain
                )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                trl_assessment, market_readiness, regulatory_assessment, 
                commercial_viability, risk_analysis, domain
            )
            
            return {
                "technology_assessment": {
                    "technology_name": technology_name,
                    "domain": domain,
                    "overall_readiness_score": overall_score,
                    "readiness_level": self._classify_readiness_level(overall_score),
                    "trl_assessment": trl_assessment,
                    "market_readiness": market_readiness,
                    "regulatory_assessment": regulatory_assessment,
                    "commercial_viability": commercial_viability
                },
                "risk_analysis": risk_analysis,
                "timeline_prediction": timeline_prediction,
                "recommendations": recommendations,
                "assessment_metadata": {
                    "assessment_criteria": assessment_criteria,
                    "domain": domain,
                    "data_sources": {
                        "research_indicators": len(research_data),
                        "market_indicators": len(market_data),
                        "regulatory_indicators": len(regulatory_data)
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"TechnologyReadinessTool execution failed: {e}")
            return {
                "error": str(e),
                "technology_assessment": {},
                "timestamp": datetime.now().isoformat()
            }
    
    def _assess_technology_readiness_level(self, research_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Assess Technology Readiness Level (TRL 1-9)."""
        
        # Standard TRL indicators
        trl_indicators = {
            "scientific_publications": research_data.get("publications_count", 0),
            "patents_filed": research_data.get("patents_count", 0),
            "prototype_exists": research_data.get("has_prototype", False),
            "lab_validation": research_data.get("lab_validated", False),
            "pilot_testing": research_data.get("pilot_tested", False),
            "field_demonstration": research_data.get("field_demonstrated", False),
            "commercial_deployment": research_data.get("commercially_deployed", False),
            "proven_operation": research_data.get("proven_in_operation", False)
        }
        
        # Calculate TRL score based on indicators
        trl_score = 1  # Base level
        
        # TRL progression logic
        if trl_indicators["scientific_publications"] > 0:
            trl_score = max(trl_score, 2)  # Basic principles observed
        
        if trl_indicators["scientific_publications"] > 10:
            trl_score = max(trl_score, 3)  # Analytical and experimental critical function
        
        if trl_indicators["lab_validation"]:
            trl_score = max(trl_score, 4)  # Component validation in lab
        
        if trl_indicators["prototype_exists"]:
            trl_score = max(trl_score, 5)  # Component validation in relevant environment
        
        if trl_indicators["pilot_testing"]:
            trl_score = max(trl_score, 6)  # System/subsystem model demonstration
        
        if trl_indicators["field_demonstration"]:
            trl_score = max(trl_score, 7)  # System prototype demonstration
        
        if trl_indicators["commercial_deployment"]:
            trl_score = max(trl_score, 8)  # System complete and qualified
        
        if trl_indicators["proven_operation"]:
            trl_score = max(trl_score, 9)  # Actual system proven in operational environment
        
        # Domain-specific adjustments
        domain_factors = self._get_domain_factors(domain)
        adjusted_score = min(9, trl_score * domain_factors.get("trl_multiplier", 1.0))
        
        return {
            "trl_level": int(adjusted_score),
            "trl_description": self._get_trl_description(int(adjusted_score)),
            "indicators_met": [k for k, v in trl_indicators.items() if v],
            "next_milestone": self._get_next_trl_milestone(int(adjusted_score)),
            "confidence": self._calculate_trl_confidence(trl_indicators, research_data)
        }
    
    def _assess_market_readiness(self, market_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Assess market readiness and adoption potential."""
        
        # Market readiness indicators
        market_size = market_data.get("total_addressable_market", 0)
        growth_rate = market_data.get("market_growth_rate", 0)
        competition_level = market_data.get("competition_intensity", "unknown")
        customer_demand = market_data.get("customer_demand_score", 0)
        adoption_barriers = market_data.get("adoption_barriers", [])
        
        # Calculate market readiness score (0-1)
        score_components = []
        
        # Market size scoring
        if market_size > 10e9:  # >$10B
            score_components.append(1.0)
        elif market_size > 1e9:  # >$1B
            score_components.append(0.8)
        elif market_size > 100e6:  # >$100M
            score_components.append(0.6)
        else:
            score_components.append(0.3)
        
        # Growth rate scoring
        if growth_rate > 0.2:  # >20% CAGR
            score_components.append(1.0)
        elif growth_rate > 0.1:  # >10% CAGR
            score_components.append(0.8)
        elif growth_rate > 0.05:  # >5% CAGR
            score_components.append(0.6)
        else:
            score_components.append(0.3)
        
        # Customer demand scoring
        demand_score = min(customer_demand / 10.0, 1.0)  # Normalize to 0-1
        score_components.append(demand_score)
        
        # Competition impact
        competition_multiplier = {
            "low": 1.0,
            "medium": 0.8,
            "high": 0.6,
            "unknown": 0.7
        }.get(competition_level, 0.7)
        
        # Adoption barriers impact
        barrier_penalty = len(adoption_barriers) * 0.1
        
        # Calculate final score
        base_score = sum(score_components) / len(score_components)
        adjusted_score = max(0, base_score * competition_multiplier - barrier_penalty)
        
        return {
            "market_readiness_score": adjusted_score,
            "market_size": market_size,
            "growth_rate": growth_rate,
            "competition_level": competition_level,
            "customer_demand": customer_demand,
            "adoption_barriers": adoption_barriers,
            "market_timing": self._assess_market_timing(adjusted_score, growth_rate),
            "key_challenges": self._identify_market_challenges(market_data, domain)
        }
    
    def _assess_regulatory_readiness(self, regulatory_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Assess regulatory environment and compliance readiness."""
        
        regulatory_approval = regulatory_data.get("regulatory_approval", "unknown")
        compliance_cost = regulatory_data.get("compliance_cost_estimate", 0)
        approval_timeline = regulatory_data.get("approval_timeline_months", 0)
        regulatory_risk = regulatory_data.get("regulatory_risk_level", "medium")
        
        # Domain-specific regulatory frameworks
        domain_regulations = {
            "biotech": {"complexity": "high", "timeline_multiplier": 2.0},
            "fintech": {"complexity": "high", "timeline_multiplier": 1.5},
            "ai": {"complexity": "medium", "timeline_multiplier": 1.2},
            "automotive": {"complexity": "high", "timeline_multiplier": 1.8},
            "aerospace": {"complexity": "very_high", "timeline_multiplier": 2.5},
            "healthcare": {"complexity": "very_high", "timeline_multiplier": 2.2},
            "energy": {"complexity": "high", "timeline_multiplier": 1.7}
        }
        
        domain_reg = domain_regulations.get(domain.lower(), {"complexity": "medium", "timeline_multiplier": 1.0})
        
        # Calculate regulatory readiness score
        approval_score = {
            "approved": 1.0,
            "in_review": 0.7,
            "pre_submission": 0.5,
            "planning": 0.3,
            "unknown": 0.2
        }.get(regulatory_approval, 0.2)
        
        risk_multiplier = {
            "low": 1.0,
            "medium": 0.8,
            "high": 0.6,
            "very_high": 0.4
        }.get(regulatory_risk, 0.8)
        
        timeline_score = max(0, 1.0 - (approval_timeline / 60.0))  # Normalize against 5 years
        
        regulatory_score = (approval_score * 0.5 + timeline_score * 0.3) * risk_multiplier
        
        return {
            "regulatory_readiness_score": regulatory_score,
            "regulatory_approval_status": regulatory_approval,
            "compliance_cost": compliance_cost,
            "approval_timeline_months": approval_timeline,
            "regulatory_risk": regulatory_risk,
            "domain_complexity": domain_reg["complexity"],
            "regulatory_challenges": self._identify_regulatory_challenges(regulatory_data, domain),
            "recommended_actions": self._recommend_regulatory_actions(regulatory_data, domain)
        }
    
    def _assess_commercial_viability(self, research_data: Dict[str, Any], 
                                   market_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Assess commercial viability and business potential."""
        
        # Extract relevant metrics
        development_cost = research_data.get("development_cost_estimate", 0)
        manufacturing_scalability = research_data.get("manufacturing_scalable", False)
        unit_economics = market_data.get("unit_economics", {})
        revenue_model = market_data.get("revenue_model", "unknown")
        competitive_advantage = market_data.get("competitive_advantage_strength", 0)
        
        # Calculate viability components
        cost_score = self._score_cost_structure(development_cost, unit_economics)
        scalability_score = 1.0 if manufacturing_scalability else 0.3
        business_model_score = self._score_business_model(revenue_model, unit_economics)
        competitive_score = min(competitive_advantage / 10.0, 1.0)
        
        # Weighted average
        weights = [0.3, 0.2, 0.3, 0.2]  # cost, scalability, business model, competitive
        scores = [cost_score, scalability_score, business_model_score, competitive_score]
        viability_score = sum(w * s for w, s in zip(weights, scores))
        
        return {
            "commercial_viability_score": viability_score,
            "cost_structure_score": cost_score,
            "scalability_score": scalability_score,
            "business_model_score": business_model_score,
            "competitive_advantage_score": competitive_score,
            "key_value_propositions": self._identify_value_propositions(market_data, domain),
            "monetization_potential": self._assess_monetization_potential(market_data),
            "scaling_challenges": self._identify_scaling_challenges(research_data, market_data)
        }
    
    def _calculate_overall_readiness(self, trl_assessment: Dict[str, Any], 
                                   market_readiness: Dict[str, Any],
                                   regulatory_assessment: Dict[str, Any],
                                   commercial_viability: Dict[str, Any]) -> float:
        """Calculate overall technology readiness score."""
        
        # Normalize TRL to 0-1 scale
        trl_score = trl_assessment["trl_level"] / 9.0
        market_score = market_readiness["market_readiness_score"]
        regulatory_score = regulatory_assessment["regulatory_readiness_score"]
        commercial_score = commercial_viability["commercial_viability_score"]
        
        # Weighted combination
        weights = [0.3, 0.25, 0.25, 0.2]  # TRL, market, regulatory, commercial
        scores = [trl_score, market_score, regulatory_score, commercial_score]
        
        overall_score = sum(w * s for w, s in zip(weights, scores))
        return min(1.0, max(0.0, overall_score))
    
    def _analyze_risks(self, research_data: Dict[str, Any], market_data: Dict[str, Any], 
                      regulatory_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Analyze risks across multiple dimensions."""
        
        technical_risks = self._assess_technical_risks(research_data, domain)
        market_risks = self._assess_market_risks(market_data, domain)
        regulatory_risks = self._assess_regulatory_risks(regulatory_data, domain)
        competitive_risks = self._assess_competitive_risks(market_data, domain)
        
        # Calculate overall risk score
        risk_scores = [
            technical_risks.get("risk_score", 0.5),
            market_risks.get("risk_score", 0.5),
            regulatory_risks.get("risk_score", 0.5),
            competitive_risks.get("risk_score", 0.5)
        ]
        overall_risk = sum(risk_scores) / len(risk_scores)
        
        return {
            "overall_risk_score": overall_risk,
            "risk_level": "high" if overall_risk > 0.7 else "medium" if overall_risk > 0.4 else "low",
            "technical_risks": technical_risks,
            "market_risks": market_risks,
            "regulatory_risks": regulatory_risks,
            "competitive_risks": competitive_risks,
            "risk_mitigation_strategies": self._recommend_risk_mitigation(
                technical_risks, market_risks, regulatory_risks, competitive_risks
            )
        }
    
    def _predict_market_timeline(self, trl_assessment: Dict[str, Any], 
                               market_readiness: Dict[str, Any],
                               regulatory_assessment: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Predict market entry and adoption timeline."""
        
        current_trl = trl_assessment["trl_level"]
        market_score = market_readiness["market_readiness_score"]
        regulatory_score = regulatory_assessment["regulatory_readiness_score"]
        
        # Base timeline estimates by TRL level
        trl_to_market_months = {
            1: 120, 2: 108, 3: 96, 4: 84, 5: 72,
            6: 60, 7: 48, 8: 24, 9: 12
        }
        
        base_timeline = trl_to_market_months.get(current_trl, 120)
        
        # Adjust for market and regulatory factors
        market_multiplier = 1.0 - (market_score * 0.3)  # Better market = faster
        regulatory_multiplier = 1.0 + ((1 - regulatory_score) * 0.5)  # More regulatory risk = slower
        
        # Domain-specific multipliers
        domain_multipliers = {
            "software": 0.5,
            "ai": 0.7,
            "fintech": 1.2,
            "biotech": 2.0,
            "healthcare": 1.8,
            "automotive": 1.5,
            "aerospace": 2.2,
            "energy": 1.6
        }
        
        domain_multiplier = domain_multipliers.get(domain.lower(), 1.0)
        
        # Calculate final timeline
        adjusted_timeline = base_timeline * market_multiplier * regulatory_multiplier * domain_multiplier
        
        return {
            "estimated_months_to_market": int(adjusted_timeline),
            "market_entry_timeline": {
                "optimistic": int(adjusted_timeline * 0.7),
                "realistic": int(adjusted_timeline),
                "pessimistic": int(adjusted_timeline * 1.5)
            },
            "key_milestones": self._generate_timeline_milestones(current_trl, int(adjusted_timeline)),
            "acceleration_opportunities": self._identify_acceleration_opportunities(
                trl_assessment, market_readiness, regulatory_assessment
            )
        }
    
    def _generate_recommendations(self, trl_assessment: Dict[str, Any], 
                                market_readiness: Dict[str, Any],
                                regulatory_assessment: Dict[str, Any],
                                commercial_viability: Dict[str, Any],
                                risk_analysis: Dict[str, Any], domain: str) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # TRL-based recommendations
        current_trl = trl_assessment["trl_level"]
        if current_trl < 5:
            recommendations.append("Focus on advancing technical development and prototype validation")
        elif current_trl < 7:
            recommendations.append("Prioritize pilot testing and field demonstrations")
        else:
            recommendations.append("Prepare for commercial deployment and scaling")
        
        # Market readiness recommendations
        market_score = market_readiness["market_readiness_score"]
        if market_score < 0.5:
            recommendations.append("Conduct deeper market research and customer validation")
        
        # Regulatory recommendations
        regulatory_score = regulatory_assessment["regulatory_readiness_score"]
        if regulatory_score < 0.6:
            recommendations.append("Engage with regulatory bodies early and develop compliance strategy")
        
        # Commercial viability recommendations
        commercial_score = commercial_viability["commercial_viability_score"]
        if commercial_score < 0.6:
            recommendations.append("Refine business model and improve unit economics")
        
        # Risk-based recommendations
        overall_risk = risk_analysis["overall_risk_score"]
        if overall_risk > 0.7:
            recommendations.append("Implement comprehensive risk mitigation strategies")
        
        # Domain-specific recommendations
        domain_recs = self._get_domain_specific_recommendations(domain, trl_assessment, market_readiness)
        recommendations.extend(domain_recs)
        
        return recommendations
    
    # Helper methods (simplified implementations)
    def _get_domain_factors(self, domain: str) -> Dict[str, float]:
        """Get domain-specific adjustment factors."""
        return {
            "software": {"trl_multiplier": 1.2},
            "ai": {"trl_multiplier": 1.1},
            "biotech": {"trl_multiplier": 0.9},
            "healthcare": {"trl_multiplier": 0.8},
        }.get(domain.lower(), {"trl_multiplier": 1.0})
    
    def _get_trl_description(self, trl: int) -> str:
        """Get TRL level description."""
        descriptions = {
            1: "Basic principles observed",
            2: "Technology concept formulated", 
            3: "Experimental proof of concept",
            4: "Technology validated in lab",
            5: "Technology validated in relevant environment",
            6: "Technology demonstrated in relevant environment",
            7: "System prototype demonstration in operational environment",
            8: "System complete and qualified",
            9: "Actual system proven in operational environment"
        }
        return descriptions.get(trl, "Unknown TRL level")
    
    def _classify_readiness_level(self, score: float) -> str:
        """Classify overall readiness level."""
        if score > 0.8:
            return "High readiness - Market ready"
        elif score > 0.6:
            return "Medium-high readiness - Near market ready"
        elif score > 0.4:
            return "Medium readiness - Development phase"
        elif score > 0.2:
            return "Low-medium readiness - Early development"
        else:
            return "Low readiness - Research phase"
    
    # Additional helper methods would be implemented here...
    def _get_next_trl_milestone(self, trl: int) -> str:
        milestones = {
            1: "Formulate technology concept",
            2: "Develop experimental proof of concept",
            3: "Validate technology in laboratory",
            4: "Validate in relevant environment",
            5: "Demonstrate in relevant environment", 
            6: "Demonstrate system prototype",
            7: "Complete and qualify system",
            8: "Prove system in operations"
        }
        return milestones.get(trl, "Technology fully mature")
    
    def _calculate_trl_confidence(self, indicators: Dict[str, Any], research_data: Dict[str, Any]) -> float:
        met_indicators = sum(1 for v in indicators.values() if v)
        total_indicators = len(indicators)
        base_confidence = met_indicators / total_indicators
        
        # Boost confidence with additional data
        data_quality = len(research_data) / 10.0  # Normalize
        return min(1.0, base_confidence + data_quality * 0.2)
    
    def _assess_market_timing(self, score: float, growth_rate: float) -> str:
        if score > 0.7 and growth_rate > 0.15:
            return "Optimal timing"
        elif score > 0.5:
            return "Good timing"
        else:
            return "Wait for better conditions"
    
    def _identify_market_challenges(self, market_data: Dict[str, Any], domain: str) -> List[str]:
        challenges = []
        if market_data.get("competition_intensity") == "high":
            challenges.append("High competition intensity")
        if market_data.get("customer_demand_score", 0) < 5:
            challenges.append("Low customer demand")
        return challenges
    
    def _score_cost_structure(self, dev_cost: float, unit_economics: Dict[str, Any]) -> float:
        # Simplified cost scoring
        if dev_cost > 100e6:  # >$100M
            return 0.3
        elif dev_cost > 10e6:  # >$10M
            return 0.6
        else:
            return 0.9
    
    def _score_business_model(self, revenue_model: str, unit_economics: Dict[str, Any]) -> float:
        model_scores = {
            "subscription": 0.9,
            "saas": 0.9,
            "marketplace": 0.8,
            "licensing": 0.7,
            "unknown": 0.4
        }
        return model_scores.get(revenue_model, 0.5)
    
    def _identify_value_propositions(self, market_data: Dict[str, Any], domain: str) -> List[str]:
        return ["Cost reduction", "Efficiency improvement", "New capabilities"]
    
    def _assess_monetization_potential(self, market_data: Dict[str, Any]) -> str:
        market_size = market_data.get("total_addressable_market", 0)
        if market_size > 10e9:
            return "High"
        elif market_size > 1e9:
            return "Medium"
        else:
            return "Low"
    
    def _identify_scaling_challenges(self, research_data: Dict[str, Any], market_data: Dict[str, Any]) -> List[str]:
        challenges = []
        if not research_data.get("manufacturing_scalable", True):
            challenges.append("Manufacturing scalability")
        return challenges
    
    # Risk assessment helper methods
    def _assess_technical_risks(self, research_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        return {"risk_score": 0.4, "risks": ["Technical complexity", "Scalability challenges"]}
    
    def _assess_market_risks(self, market_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        return {"risk_score": 0.3, "risks": ["Market adoption", "Competition"]}
    
    def _assess_regulatory_risks(self, regulatory_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        return {"risk_score": 0.5, "risks": ["Regulatory approval", "Compliance costs"]}
    
    def _assess_competitive_risks(self, market_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        return {"risk_score": 0.4, "risks": ["Competitive response", "Market entry barriers"]}
    
    def _recommend_risk_mitigation(self, *risk_assessments) -> List[str]:
        return ["Diversify development approaches", "Build strategic partnerships", "Monitor regulatory changes"]
    
    def _generate_timeline_milestones(self, current_trl: int, months_to_market: int) -> List[Dict[str, Any]]:
        milestones = []
        remaining_months = months_to_market
        
        for trl in range(current_trl + 1, 10):
            months_for_trl = remaining_months // (9 - current_trl)
            milestones.append({
                "milestone": f"Achieve TRL {trl}",
                "estimated_months": months_for_trl,
                "description": self._get_trl_description(trl)
            })
            remaining_months -= months_for_trl
        
        return milestones
    
    def _identify_acceleration_opportunities(self, *assessments) -> List[str]:
        return ["Strategic partnerships", "Government funding", "Regulatory fast-track programs"]
    
    def _identify_regulatory_challenges(self, regulatory_data: Dict[str, Any], domain: str) -> List[str]:
        return ["Approval timeline uncertainty", "Compliance complexity"]
    
    def _recommend_regulatory_actions(self, regulatory_data: Dict[str, Any], domain: str) -> List[str]:
        return ["Engage regulatory consultants", "Submit pre-application meetings"]
    
    def _get_domain_specific_recommendations(self, domain: str, trl_assessment: Dict[str, Any], market_readiness: Dict[str, Any]) -> List[str]:
        return [f"Focus on {domain}-specific validation requirements"]

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return the input schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "technology_name": {
                    "type": "string",
                    "description": "Name of the technology to assess"
                },
                "domain": {
                    "type": "string",
                    "description": "Technology domain (e.g., 'AI', 'biotech', 'fintech')"
                },
                "research_data": {
                    "type": "object",
                    "description": "Research and development indicators",
                    "properties": {
                        "publications_count": {"type": "integer"},
                        "patents_count": {"type": "integer"},
                        "has_prototype": {"type": "boolean"},
                        "lab_validated": {"type": "boolean"},
                        "development_cost_estimate": {"type": "number"}
                    }
                },
                "market_data": {
                    "type": "object",
                    "description": "Market and adoption indicators",
                    "properties": {
                        "total_addressable_market": {"type": "number"},
                        "market_growth_rate": {"type": "number"},
                        "competition_intensity": {"type": "string"},
                        "customer_demand_score": {"type": "number"}
                    }
                },
                "regulatory_data": {
                    "type": "object",
                    "description": "Regulatory and compliance indicators",
                    "properties": {
                        "regulatory_approval": {"type": "string"},
                        "approval_timeline_months": {"type": "integer"},
                        "regulatory_risk_level": {"type": "string"}
                    }
                },
                "assessment_criteria": {
                    "type": "string",
                    "default": "standard",
                    "description": "Assessment criteria to use"
                },
                "include_timeline": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include timeline predictions"
                }
            },
            "required": ["technology_name", "domain"]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return the output schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "technology_assessment": {
                    "type": "object",
                    "description": "Comprehensive technology readiness assessment"
                },
                "risk_analysis": {
                    "type": "object",
                    "description": "Multi-dimensional risk analysis"
                },
                "timeline_prediction": {
                    "type": "object",
                    "description": "Market entry timeline predictions"
                },
                "recommendations": {
                    "type": "array",
                    "description": "Actionable recommendations"
                },
                "assessment_metadata": {
                    "type": "object",
                    "description": "Assessment parameters and metadata"
                },
                "timestamp": {
                    "type": "string",
                    "description": "When the assessment was performed"
                }
            }
        } 