"""
Comprehensive Burnout Analysis Workflow

Orchestrates multi-step analysis using smolagents for team-wide burnout detection.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import asyncio

from ..burnout_agent import BurnoutDetectionAgent

logger = logging.getLogger(__name__)


class ComprehensiveBurnoutWorkflow:
    """
    Structured workflow for comprehensive burnout analysis using smolagents.
    
    This workflow orchestrates:
    1. Individual member analysis with AI reasoning
    2. Team-wide pattern detection
    3. Cross-member correlation analysis
    4. Predictive risk assessment
    5. Intervention planning
    """
    
    def __init__(self, agent: BurnoutDetectionAgent):
        """
        Initialize workflow with a configured burnout detection agent.
        
        Args:
            agent: Configured BurnoutDetectionAgent instance
        """
        self.agent = agent
        self.logger = logging.getLogger(__name__)
        
    async def run_comprehensive_analysis(
        self, 
        team_data: List[Dict[str, Any]],
        available_data_sources: List[str],
        historical_data: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive team burnout analysis.
        
        Args:
            team_data: List of team member data
            available_data_sources: Available data platforms
            historical_data: Optional historical analyses for trend analysis
            
        Returns:
            Comprehensive analysis results with individual and team insights
        """
        self.logger.info(f"Starting comprehensive workflow for {len(team_data)} team members")
        
        workflow_results = {
            "workflow_id": f"workflow_{datetime.utcnow().isoformat()}",
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "team_size": len(team_data),
            "data_sources": available_data_sources,
            "phases": {}
        }
        
        try:
            # Phase 1: Individual Analysis
            self.logger.info("Phase 1: Running individual member analyses")
            individual_results = await self._phase1_individual_analysis(
                team_data, available_data_sources
            )
            workflow_results["phases"]["individual_analysis"] = individual_results
            
            # Phase 2: Team Pattern Analysis
            self.logger.info("Phase 2: Analyzing team-wide patterns")
            team_patterns = await self._phase2_team_patterns(
                individual_results["analyses"], available_data_sources
            )
            workflow_results["phases"]["team_patterns"] = team_patterns
            
            # Phase 3: Cross-Member Correlation
            self.logger.info("Phase 3: Finding cross-member correlations")
            correlations = await self._phase3_cross_correlations(
                individual_results["analyses"], team_patterns
            )
            workflow_results["phases"]["correlations"] = correlations
            
            # Phase 4: Predictive Analysis
            if historical_data:
                self.logger.info("Phase 4: Running predictive analysis")
                predictions = await self._phase4_predictions(
                    individual_results["analyses"], historical_data
                )
                workflow_results["phases"]["predictions"] = predictions
            
            # Phase 5: Intervention Planning
            self.logger.info("Phase 5: Generating intervention plan")
            interventions = await self._phase5_interventions(workflow_results)
            workflow_results["phases"]["interventions"] = interventions
            
            # Generate executive summary
            workflow_results["executive_summary"] = self._generate_executive_summary(
                workflow_results
            )
            
            return workflow_results
            
        except Exception as e:
            self.logger.error(f"Workflow error: {e}")
            workflow_results["error"] = str(e)
            return workflow_results
    
    async def _phase1_individual_analysis(
        self, 
        team_data: List[Dict], 
        data_sources: List[str]
    ) -> Dict[str, Any]:
        """Phase 1: Analyze each team member individually."""
        individual_analyses = []
        high_risk_members = []
        
        # Run analyses concurrently for efficiency
        tasks = []
        for member in team_data:
            task = self._analyze_member_with_context(member, data_sources, team_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Process results
        for member, analysis in zip(team_data, results):
            member_name = member.get("name", "Unknown")
            
            if analysis and not analysis.get("error"):
                individual_analyses.append({
                    "member_name": member_name,
                    "analysis": analysis,
                    "risk_level": analysis.get("risk_assessment", {}).get("overall_risk_level", "unknown")
                })
                
                # Track high-risk members
                if analysis.get("risk_assessment", {}).get("risk_score", 0) >= 60:
                    high_risk_members.append({
                        "name": member_name,
                        "risk_score": analysis["risk_assessment"]["risk_score"],
                        "primary_factors": analysis["risk_assessment"].get("risk_factors", [])[:3]
                    })
        
        return {
            "total_analyzed": len(individual_analyses),
            "high_risk_count": len(high_risk_members),
            "high_risk_members": high_risk_members,
            "analyses": individual_analyses
        }
    
    async def _analyze_member_with_context(
        self, 
        member_data: Dict, 
        data_sources: List[str],
        team_data: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze individual member with team context."""
        try:
            # Calculate team context for comparison
            team_context = self._calculate_team_context(team_data)
            
            # Run agent analysis
            return self.agent.analyze_member_burnout(
                member_data, 
                data_sources,
                team_context
            )
        except Exception as e:
            self.logger.error(f"Error analyzing member {member_data.get('name')}: {e}")
            return {"error": str(e)}
    
    async def _phase2_team_patterns(
        self, 
        individual_analyses: List[Dict], 
        data_sources: List[str]
    ) -> Dict[str, Any]:
        """Phase 2: Detect team-wide patterns."""
        patterns = {
            "common_risk_factors": {},
            "temporal_patterns": {},
            "workload_distribution": {},
            "team_health_metrics": {}
        }
        
        # Aggregate risk factors
        all_risk_factors = []
        for analysis in individual_analyses:
            factors = analysis["analysis"].get("risk_assessment", {}).get("risk_factors", [])
            all_risk_factors.extend(factors)
        
        # Count factor frequency
        factor_counts = {}
        for factor in all_risk_factors:
            factor_counts[factor] = factor_counts.get(factor, 0) + 1
        
        # Find common patterns (affecting >30% of team)
        team_size = len(individual_analyses)
        patterns["common_risk_factors"] = {
            factor: count for factor, count in factor_counts.items()
            if count > team_size * 0.3
        }
        
        # Analyze temporal patterns
        if self.agent.agent_available:
            temporal_prompt = f"""
Analyze team-wide temporal patterns from these individual analyses:

Team size: {team_size}
Common risk factors: {patterns['common_risk_factors']}

Look for:
1. Synchronized stress patterns (multiple members stressed at same times)
2. Cascade effects (one member's burnout affecting others)
3. Team-wide work rhythm issues
4. Communication breakdown patterns

Provide insights on team dynamics and systemic issues.
"""
            
            temporal_analysis = self.agent.agent.run(temporal_prompt)
            patterns["temporal_patterns"] = {
                "analysis": temporal_analysis,
                "synchronized_stress": self._detect_synchronized_stress(individual_analyses)
            }
        
        # Calculate team health metrics
        risk_scores = [
            a["analysis"].get("risk_assessment", {}).get("risk_score", 0)
            for a in individual_analyses
        ]
        
        patterns["team_health_metrics"] = {
            "average_risk_score": sum(risk_scores) / len(risk_scores) if risk_scores else 0,
            "risk_distribution": self._calculate_risk_distribution(individual_analyses),
            "health_disparity": max(risk_scores) - min(risk_scores) if risk_scores else 0
        }
        
        return patterns
    
    async def _phase3_cross_correlations(
        self, 
        individual_analyses: List[Dict],
        team_patterns: Dict
    ) -> Dict[str, Any]:
        """Phase 3: Find cross-member correlations."""
        correlations = {
            "workload_imbalances": [],
            "stress_contagion": [],
            "collaboration_impacts": [],
            "dependency_chains": []
        }
        
        # Detect workload imbalances
        workload_data = []
        for analysis in individual_analyses:
            member_name = analysis["member_name"]
            workload = analysis["analysis"].get("ai_insights", {}).get("workload", {})
            if workload:
                workload_data.append({
                    "member": member_name,
                    "status": workload.get("workload_status", "unknown"),
                    "incident_percentage": workload.get("incident_percentage", 0)
                })
        
        # Find imbalances
        if workload_data:
            avg_incident_load = sum(w["incident_percentage"] for w in workload_data) / len(workload_data)
            for member_data in workload_data:
                if member_data["incident_percentage"] > avg_incident_load * 1.5:
                    correlations["workload_imbalances"].append({
                        "member": member_data["member"],
                        "overload_factor": member_data["incident_percentage"] / avg_incident_load,
                        "recommendation": f"Redistribute workload from {member_data['member']}"
                    })
        
        # Detect stress contagion patterns
        if self.agent.agent_available and len(individual_analyses) > 3:
            contagion_prompt = f"""
Analyze potential stress contagion patterns in this team:

Team analyses summary:
{self._summarize_for_llm(individual_analyses)}

Look for:
1. Members whose stress might be affecting others
2. Communication patterns that spread negativity
3. Incident response patterns causing team-wide stress
4. Collaborative bottlenecks

Identify specific member-to-member stress propagation.
"""
            
            contagion_analysis = self.agent.agent.run(contagion_prompt)
            correlations["stress_contagion"] = self._parse_contagion_analysis(contagion_analysis)
        
        return correlations
    
    async def _phase4_predictions(
        self, 
        individual_analyses: List[Dict],
        historical_data: List[Dict]
    ) -> Dict[str, Any]:
        """Phase 4: Predict future burnout risks."""
        predictions = {
            "team_trajectory": "unknown",
            "at_risk_members": [],
            "critical_timeframes": {},
            "preventive_actions": []
        }
        
        # Use burnout predictor tool for each member
        for analysis in individual_analyses:
            member_name = analysis["member_name"]
            current_metrics = {
                "burnout_score": analysis["analysis"].get("risk_assessment", {}).get("risk_score", 0) / 10,
                "incident_count": len(analysis["analysis"].get("member_data", {}).get("incidents", [])),
                # Add other metrics as available
            }
            
            # Get historical data for this member
            member_history = [
                h for h in historical_data 
                if h.get("member_name") == member_name
            ]
            
            if member_history:
                prediction = self.agent.burnout_predictor(
                    member_history, 
                    current_metrics,
                    time_horizon_days=30
                )
                
                if prediction.get("predicted_risk_level") in ["high", "critical"]:
                    predictions["at_risk_members"].append({
                        "member": member_name,
                        "current_risk": analysis["analysis"].get("risk_assessment", {}).get("overall_risk_level"),
                        "predicted_risk": prediction["predicted_risk_level"],
                        "days_to_critical": prediction.get("predicted_timeline", {}).get("burnout_score", {}).get("days_to_critical"),
                        "early_warnings": prediction.get("early_warning_signals", [])[:2]
                    })
        
        # Determine team trajectory
        if len(predictions["at_risk_members"]) > len(individual_analyses) * 0.5:
            predictions["team_trajectory"] = "critical_deterioration"
        elif len(predictions["at_risk_members"]) > len(individual_analyses) * 0.3:
            predictions["team_trajectory"] = "concerning_trend"
        else:
            predictions["team_trajectory"] = "manageable"
        
        return predictions
    
    async def _phase5_interventions(self, workflow_results: Dict) -> Dict[str, Any]:
        """Phase 5: Generate comprehensive intervention plan."""
        interventions = {
            "immediate_actions": [],
            "short_term_plan": [],
            "long_term_strategy": [],
            "success_metrics": []
        }
        
        # Extract key data from previous phases
        individual_phase = workflow_results["phases"].get("individual_analysis", {})
        team_patterns = workflow_results["phases"].get("team_patterns", {})
        correlations = workflow_results["phases"].get("correlations", {})
        predictions = workflow_results["phases"].get("predictions", {})
        
        # Immediate actions for high-risk members
        for member in individual_phase.get("high_risk_members", []):
            interventions["immediate_actions"].append({
                "action": f"1:1 intervention with {member['name']}",
                "urgency": "within_24_hours",
                "focus_areas": member["primary_factors"][:2],
                "expected_outcome": "Stabilize immediate burnout risk"
            })
        
        # Address workload imbalances
        for imbalance in correlations.get("workload_imbalances", []):
            interventions["immediate_actions"].append({
                "action": f"Redistribute workload from {imbalance['member']}",
                "urgency": "within_48_hours",
                "details": f"Currently handling {imbalance['overload_factor']:.1f}x average load",
                "expected_outcome": "Reduce primary stress driver"
            })
        
        # Short-term plan based on common patterns
        common_factors = team_patterns.get("common_risk_factors", {})
        for factor, count in list(common_factors.items())[:3]:
            interventions["short_term_plan"].append({
                "action": f"Address team-wide issue: {factor}",
                "timeline": "1-2_weeks",
                "affected_members": count,
                "approach": self._get_intervention_approach(factor)
            })
        
        # Long-term strategy
        if predictions.get("team_trajectory") in ["critical_deterioration", "concerning_trend"]:
            interventions["long_term_strategy"].append({
                "action": "Comprehensive team restructuring",
                "timeline": "1-3_months",
                "components": [
                    "Review and optimize on-call rotation",
                    "Implement sustainable work practices",
                    "Establish burnout prevention protocols"
                ]
            })
        
        # Define success metrics
        interventions["success_metrics"] = [
            {
                "metric": "High-risk member reduction",
                "target": "Reduce from {current} to <2 within 30 days".format(
                    current=individual_phase.get("high_risk_count", 0)
                ),
                "measurement": "Weekly burnout assessments"
            },
            {
                "metric": "Team health score improvement",
                "target": "Improve average risk score by 20%",
                "measurement": "Monthly team analysis"
            }
        ]
        
        return interventions
    
    def _calculate_team_context(self, team_data: List[Dict]) -> Dict[str, Any]:
        """Calculate team-wide context for comparison."""
        total_incidents = sum(len(m.get("incidents", [])) for m in team_data)
        team_size = len(team_data)
        
        return {
            "team_size": team_size,
            "total_incidents": total_incidents,
            "avg_incidents_per_member": total_incidents / team_size if team_size > 0 else 0,
            "members_with_incidents": sum(1 for m in team_data if m.get("incidents"))
        }
    
    def _calculate_risk_distribution(self, analyses: List[Dict]) -> Dict[str, int]:
        """Calculate distribution of risk levels."""
        distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        for analysis in analyses:
            risk_level = analysis["analysis"].get("risk_assessment", {}).get("overall_risk_level", "unknown")
            if risk_level in distribution:
                distribution[risk_level] += 1
                
        return distribution
    
    def _detect_synchronized_stress(self, analyses: List[Dict]) -> List[Dict]:
        """Detect synchronized stress patterns across team."""
        # This would analyze temporal patterns to find simultaneity
        # Simplified for now
        high_stress_members = [
            a["member_name"] for a in analyses
            if a["analysis"].get("risk_assessment", {}).get("risk_score", 0) >= 70
        ]
        
        if len(high_stress_members) > len(analyses) * 0.4:
            return [{
                "pattern": "team_wide_stress_spike",
                "affected_members": high_stress_members,
                "severity": "high"
            }]
        
        return []
    
    def _summarize_for_llm(self, analyses: List[Dict]) -> str:
        """Create concise summary for LLM analysis."""
        summary_lines = []
        
        for analysis in analyses[:10]:  # Limit to prevent token overflow
            member = analysis["member_name"]
            risk = analysis["analysis"].get("risk_assessment", {})
            factors = risk.get("risk_factors", [])[:2]
            
            summary_lines.append(
                f"- {member}: {risk.get('overall_risk_level', 'unknown')} risk, "
                f"score {risk.get('risk_score', 0)}, factors: {', '.join(factors)}"
            )
        
        return "\n".join(summary_lines)
    
    def _parse_contagion_analysis(self, llm_response: str) -> List[Dict]:
        """Parse LLM response about stress contagion."""
        # In production, implement proper parsing
        # For now, return structured placeholder
        return [{
            "type": "stress_propagation",
            "description": llm_response[:200],
            "severity": "medium"
        }]
    
    def _get_intervention_approach(self, risk_factor: str) -> str:
        """Get intervention approach for common risk factors."""
        approaches = {
            "high workload": "Implement workload balancing and capacity planning",
            "after-hours work": "Establish clear boundaries and on-call rotation",
            "incident overload": "Improve system reliability and incident prevention",
            "negative sentiment": "Team building and communication workshops",
            "code quality decline": "Technical debt reduction sprint"
        }
        
        for key, approach in approaches.items():
            if key in risk_factor.lower():
                return approach
                
        return "Targeted intervention based on root cause analysis"
    
    def _generate_executive_summary(self, workflow_results: Dict) -> Dict[str, Any]:
        """Generate executive summary of workflow results."""
        individual = workflow_results["phases"].get("individual_analysis", {})
        patterns = workflow_results["phases"].get("team_patterns", {})
        predictions = workflow_results["phases"].get("predictions", {})
        
        return {
            "team_health_status": self._determine_overall_status(workflow_results),
            "key_findings": [
                f"{individual.get('high_risk_count', 0)} team members at high burnout risk",
                f"Average team risk score: {patterns.get('team_health_metrics', {}).get('average_risk_score', 0):.1f}",
                f"Team trajectory: {predictions.get('team_trajectory', 'unknown')}"
            ],
            "critical_actions": workflow_results["phases"].get("interventions", {}).get("immediate_actions", [])[:3],
            "confidence_level": self._calculate_workflow_confidence(workflow_results)
        }
    
    def _determine_overall_status(self, results: Dict) -> str:
        """Determine overall team health status."""
        high_risk_count = results["phases"].get("individual_analysis", {}).get("high_risk_count", 0)
        team_size = results.get("team_size", 1)
        
        high_risk_ratio = high_risk_count / team_size if team_size > 0 else 0
        
        if high_risk_ratio > 0.5:
            return "critical"
        elif high_risk_ratio > 0.3:
            return "concerning" 
        elif high_risk_ratio > 0.1:
            return "moderate"
        else:
            return "healthy"
    
    def _calculate_workflow_confidence(self, results: Dict) -> float:
        """Calculate confidence in workflow results."""
        # Base confidence on data completeness and analysis success
        phases_completed = len([p for p in results.get("phases", {}).values() if p])
        total_phases = 5
        
        base_confidence = phases_completed / total_phases
        
        # Adjust based on data sources
        data_source_multiplier = min(len(results.get("data_sources", [])) * 0.3, 1.0)
        
        return round(base_confidence * data_source_multiplier, 2)


async def run_team_analysis_workflow(
    agent: BurnoutDetectionAgent,
    team_data: List[Dict[str, Any]],
    available_data_sources: List[str],
    historical_data: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Convenience function to run comprehensive team analysis workflow.
    
    Args:
        agent: Configured BurnoutDetectionAgent
        team_data: Team member data
        available_data_sources: Available data platforms
        historical_data: Optional historical analyses
        
    Returns:
        Comprehensive workflow results
    """
    workflow = ComprehensiveBurnoutWorkflow(agent)
    return await workflow.run_comprehensive_analysis(
        team_data, 
        available_data_sources,
        historical_data
    )