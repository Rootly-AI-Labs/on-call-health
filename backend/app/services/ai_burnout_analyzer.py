"""
AI-Enhanced Burnout Analysis Service

Integrates the smolagents-powered burnout detection agent with the existing analysis pipeline.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..agents.burnout_agent import create_burnout_agent

logger = logging.getLogger(__name__)

# Global user context for AI analysis
_current_user = None

def set_user_context(user):
    """Set the current user context for AI analysis."""
    global _current_user
    _current_user = user

def get_user_context():
    """Get the current user context."""
    return _current_user


class AIBurnoutAnalyzerService:
    """
    Service that adds AI-powered insights to the existing burnout analysis.
    
    This service works alongside the traditional burnout analysis to provide:
    - Dynamic, context-aware analysis
    - Intelligent recommendations
    - Pattern recognition across multiple data sources
    - Sentiment analysis integration
    """
    
    def __init__(self):
        """Initialize the AI burnout analyzer service."""
        self.logger = logging.getLogger(__name__)
        
        try:
            self.agent = create_burnout_agent()
            self.available = True
            self.logger.info("AI Burnout Analyzer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize AI agent: {e}")
            self.available = False
    
    def enhance_member_analysis(
        self,
        member_data: Dict[str, Any],
        traditional_analysis: Dict[str, Any],
        available_integrations: List[str]
    ) -> Dict[str, Any]:
        """
        Enhance traditional burnout analysis with AI insights.
        
        Args:
            member_data: Raw member data from all sources
            traditional_analysis: Results from traditional burnout analysis
            available_integrations: List of available data sources
            
        Returns:
            Enhanced analysis with AI insights
        """
        if not self.available:
            return self._add_unavailable_notice(traditional_analysis)
        
        try:
            # Prepare data for AI analysis
            ai_member_data = self._prepare_ai_data(member_data, available_integrations)
            
            # Get AI analysis
            ai_insights = self.agent.analyze_member_burnout(
                ai_member_data,
                available_integrations
            )
            
            # Merge AI insights with traditional analysis
            enhanced_analysis = self._merge_analyses(traditional_analysis, ai_insights)
            
            return enhanced_analysis
            
        except Exception as e:
            self.logger.error(f"Error in AI analysis enhancement: {e}")
            return self._add_error_notice(traditional_analysis, str(e))
    
    def generate_team_insights(
        self,
        team_members: List[Dict[str, Any]],
        available_integrations: List[str]
    ) -> Dict[str, Any]:
        """
        Generate team-level AI insights and recommendations.
        
        Args:
            team_members: List of team member analyses
            available_integrations: Available data sources
            
        Returns:
            Team-level AI insights
        """
        if not self.available:
            return {"available": False, "message": "AI insights not available"}
        
        try:
            # Analyze team patterns
            team_insights = {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "team_size": len(team_members),
                "data_sources": available_integrations,
                "risk_distribution": self._analyze_team_risk_distribution(team_members),
                "common_patterns": self._identify_common_patterns(team_members),
                "team_recommendations": self._generate_team_recommendations(team_members),
                "workload_distribution": self._analyze_workload_distribution(team_members)
            }
            
            return {"available": True, "insights": team_insights}
            
        except Exception as e:
            self.logger.error(f"Error generating team insights: {e}")
            return {"available": False, "error": str(e)}
    
    def _prepare_ai_data(self, member_data: Dict[str, Any], integrations: List[str]) -> Dict[str, Any]:
        """
        Transform member data into format expected by AI agent.
        """
        ai_data = {
            "name": member_data.get("user_name", "Unknown"),
            "user_id": member_data.get("user_id"),
            "incidents": [],
            "commits": [],
            "pull_requests": [],
            "messages": [],
            "slack_messages": [],
            "pr_comments": [],
            "incident_comments": []
        }
        
        # Add incident data
        if "incidents" in member_data:
            for incident in member_data["incidents"]:
                ai_data["incidents"].append({
                    "timestamp": incident.get("created_at") or incident.get("timestamp"),
                    "severity": incident.get("severity"),
                    "response_time_minutes": incident.get("acknowledged_at_minutes"),
                    "resolved_at": incident.get("resolved_at"),
                    "urgency": incident.get("urgency")
                })
        
        # Add GitHub data if available
        if "github" in integrations and member_data.get("github_activity"):
            github_data = member_data["github_activity"]
            
            # Add commits
            if "commits" in github_data:
                for commit in github_data["commits"]:
                    ai_data["commits"].append({
                        "timestamp": commit.get("created_at") or commit.get("timestamp"),
                        "changes": commit.get("additions", 0) + commit.get("deletions", 0),
                        "message": commit.get("message", "")
                    })
            
            # Add pull requests
            if "pull_requests" in github_data:
                for pr in github_data["pull_requests"]:
                    ai_data["pull_requests"].append({
                        "timestamp": pr.get("created_at") or pr.get("timestamp"),
                        "size": pr.get("additions", 0) + pr.get("deletions", 0),
                        "title": pr.get("title", ""),
                        "state": pr.get("state")
                    })
        
        # Add Slack data if available
        if "slack" in integrations and member_data.get("slack_activity"):
            slack_data = member_data["slack_activity"]
            
            # Add messages
            if "messages" in slack_data:
                for message in slack_data["messages"]:
                    ai_data["messages"].append({
                        "timestamp": message.get("created_at") or message.get("timestamp"),
                        "text": message.get("text", ""),
                        "channel": message.get("channel")
                    })
                    
                    # Also add to slack_messages for sentiment analysis
                    ai_data["slack_messages"].append({
                        "text": message.get("text", ""),
                        "timestamp": message.get("created_at") or message.get("timestamp")
                    })
        
        return ai_data
    
    def _merge_analyses(self, traditional: Dict[str, Any], ai_insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge traditional analysis with AI insights.
        """
        enhanced = traditional.copy()
        
        # Add AI insights section
        enhanced["ai_insights"] = ai_insights.get("ai_insights", {})
        
        # Enhance risk assessment
        ai_risk = ai_insights.get("risk_assessment", {})
        if ai_risk:
            enhanced["ai_risk_assessment"] = ai_risk
            
            # If AI detected higher risk, flag it
            traditional_risk = enhanced.get("risk_level", "low")
            ai_risk_level = ai_risk.get("overall_risk_level", "low")
            
            if self._risk_level_value(ai_risk_level) > self._risk_level_value(traditional_risk):
                enhanced["risk_level"] = ai_risk_level
                enhanced["risk_escalated_by_ai"] = True
        
        # Add AI recommendations
        ai_recommendations = ai_insights.get("recommendations", [])
        if ai_recommendations:
            enhanced["ai_recommendations"] = ai_recommendations
            
            # Add high-priority AI recommendations to main recommendations
            urgent_ai_recs = [rec for rec in ai_recommendations if rec.get("priority") in ["urgent", "high"]]
            if urgent_ai_recs:
                if "recommendations" not in enhanced:
                    enhanced["recommendations"] = []
                
                for rec in urgent_ai_recs:
                    enhanced["recommendations"].append(f"[AI] {rec['description']}")
        
        # Add confidence and analysis metadata
        enhanced["ai_confidence"] = ai_insights.get("confidence_score", 0.0)
        enhanced["ai_analysis_timestamp"] = ai_insights.get("analysis_timestamp")
        enhanced["ai_data_sources"] = ai_insights.get("data_sources_analyzed", [])
        
        return enhanced
    
    def _risk_level_value(self, risk_level: str) -> int:
        """Convert risk level to numeric value for comparison."""
        levels = {"low": 1, "medium": 2, "moderate": 2, "high": 3, "critical": 4}
        return levels.get(risk_level.lower(), 1)
    
    def _analyze_team_risk_distribution(self, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze risk distribution across the team."""
        risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        ai_escalations = 0
        
        for member in team_members:
            risk_level = member.get("risk_level", "low").lower()
            if risk_level in risk_counts:
                risk_counts[risk_level] += 1
            
            if member.get("risk_escalated_by_ai"):
                ai_escalations += 1
        
        total = len(team_members)
        high_risk_count = risk_counts["high"] + risk_counts["critical"]
        
        return {
            "distribution": risk_counts,
            "high_risk_percentage": (high_risk_count / total * 100) if total > 0 else 0,
            "ai_escalations": ai_escalations,
            "total_members": total
        }
    
    def _identify_common_patterns(self, team_members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common patterns across team members."""
        patterns = []
        
        # Count common AI-identified issues
        issue_counts = {}
        
        for member in team_members:
            ai_risk = member.get("ai_risk_assessment", {})
            risk_factors = ai_risk.get("risk_factors", [])
            
            for factor in risk_factors:
                # Extract pattern type from risk factor
                pattern_key = self._extract_pattern_type(factor)
                if pattern_key:
                    issue_counts[pattern_key] = issue_counts.get(pattern_key, 0) + 1
        
        # Identify patterns affecting multiple team members
        team_size = len(team_members)
        threshold = max(2, team_size * 0.3)  # At least 2 members or 30% of team
        
        for pattern, count in issue_counts.items():
            if count >= threshold:
                patterns.append({
                    "pattern": pattern,
                    "affected_members": count,
                    "percentage": (count / team_size * 100) if team_size > 0 else 0,
                    "severity": "high" if count >= team_size * 0.5 else "medium"
                })
        
        return sorted(patterns, key=lambda x: x["affected_members"], reverse=True)
    
    def _extract_pattern_type(self, risk_factor: str) -> Optional[str]:
        """Extract pattern type from risk factor description."""
        risk_factor_lower = risk_factor.lower()
        
        if "after-hours" in risk_factor_lower or "after hours" in risk_factor_lower:
            return "after_hours_work"
        elif "weekend" in risk_factor_lower:
            return "weekend_work"
        elif "incident" in risk_factor_lower and ("load" in risk_factor_lower or "response" in risk_factor_lower):
            return "incident_overload"
        elif "negative" in risk_factor_lower and "sentiment" in risk_factor_lower:
            return "communication_stress"
        elif "workload" in risk_factor_lower:
            return "high_workload"
        elif "coding" in risk_factor_lower or "commit" in risk_factor_lower:
            return "excessive_coding"
        elif "communication" in risk_factor_lower and "overload" in risk_factor_lower:
            return "communication_overload"
        
        return None
    
    def _generate_team_recommendations(self, team_members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate team-level recommendations based on AI analysis."""
        recommendations = []
        
        # Analyze common patterns
        common_patterns = self._identify_common_patterns(team_members)
        
        for pattern in common_patterns:
            if pattern["severity"] == "high":
                rec = self._get_team_recommendation_for_pattern(pattern["pattern"], pattern["affected_members"])
                if rec:
                    recommendations.append(rec)
        
        # Overall team health recommendations
        risk_dist = self._analyze_team_risk_distribution(team_members)
        high_risk_pct = risk_dist["high_risk_percentage"]
        
        if high_risk_pct > 30:
            recommendations.append({
                "priority": "urgent",
                "category": "team_health",
                "title": "Team Burnout Risk Critical",
                "description": f"{high_risk_pct:.1f}% of team members show high burnout risk",
                "actions": [
                    "Conduct immediate team workload review",
                    "Implement team-wide stress reduction measures",
                    "Consider bringing in additional resources",
                    "Review team processes and efficiency"
                ]
            })
        elif high_risk_pct > 15:
            recommendations.append({
                "priority": "high",
                "category": "team_health", 
                "title": "Team Burnout Prevention",
                "description": f"{high_risk_pct:.1f}% of team members show elevated burnout risk",
                "actions": [
                    "Monitor team workload trends closely",
                    "Implement preventive measures",
                    "Improve team communication and support"
                ]
            })
        
        return recommendations
    
    def _get_team_recommendation_for_pattern(self, pattern: str, affected_count: int) -> Optional[Dict[str, Any]]:
        """Get team recommendation for a specific pattern."""
        if pattern == "after_hours_work":
            return {
                "priority": "high",
                "category": "work_life_balance",
                "title": "Team After-Hours Work Issue",
                "description": f"{affected_count} team members showing excessive after-hours work",
                "actions": [
                    "Establish team-wide after-hours boundaries",
                    "Review on-call rotation effectiveness",
                    "Implement better workload planning"
                ]
            }
        elif pattern == "weekend_work":
            return {
                "priority": "high",
                "category": "work_life_balance",
                "title": "Team Weekend Work Pattern",
                "description": f"{affected_count} team members frequently working weekends",
                "actions": [
                    "Review sprint planning and estimation",
                    "Establish weekend work policies",
                    "Improve task prioritization"
                ]
            }
        elif pattern == "incident_overload":
            return {
                "priority": "urgent",
                "category": "operational",
                "title": "Team Incident Overload",
                "description": f"{affected_count} team members experiencing incident response overload",
                "actions": [
                    "Expand incident response team",
                    "Improve monitoring and prevention",
                    "Review incident severity classification"
                ]
            }
        elif pattern == "communication_stress":
            return {
                "priority": "medium",
                "category": "team_dynamics",
                "title": "Team Communication Health",
                "description": f"{affected_count} team members showing communication stress indicators",
                "actions": [
                    "Conduct team communication workshop",
                    "Review team collaboration processes",
                    "Provide conflict resolution support"
                ]
            }
        
        return None
    
    def _analyze_workload_distribution(self, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze workload distribution across the team."""
        workload_data = []
        
        for member in team_members:
            ai_insights = member.get("ai_insights", {})
            workload_info = ai_insights.get("workload", {})
            
            if workload_info:
                workload_data.append({
                    "member": member.get("user_name", "Unknown"),
                    "intensity": workload_info.get("intensity_score", 0),
                    "status": workload_info.get("workload_status", "unknown")
                })
        
        if not workload_data:
            return {"available": False}
        
        # Calculate distribution metrics
        intensities = [w["intensity"] for w in workload_data]
        avg_intensity = sum(intensities) / len(intensities) if intensities else 0
        max_intensity = max(intensities) if intensities else 0
        min_intensity = min(intensities) if intensities else 0
        
        # Find imbalances
        imbalance_threshold = 30  # intensity points
        imbalanced_pairs = []
        
        for i, member1 in enumerate(workload_data):
            for member2 in workload_data[i+1:]:
                diff = abs(member1["intensity"] - member2["intensity"])
                if diff > imbalance_threshold:
                    imbalanced_pairs.append({
                        "high_load": member1["member"] if member1["intensity"] > member2["intensity"] else member2["member"],
                        "low_load": member2["member"] if member1["intensity"] > member2["intensity"] else member1["member"],
                        "difference": diff
                    })
        
        return {
            "available": True,
            "average_intensity": round(avg_intensity, 1),
            "intensity_range": {"min": min_intensity, "max": max_intensity},
            "imbalances": imbalanced_pairs,
            "distribution_health": "poor" if len(imbalanced_pairs) > len(workload_data) * 0.3 else "good"
        }
    
    def _add_unavailable_notice(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Add notice that AI analysis is unavailable."""
        analysis = analysis.copy()
        analysis["ai_available"] = False
        analysis["ai_notice"] = "AI-enhanced analysis not available. Using traditional analysis only."
        return analysis
    
    def _add_error_notice(self, analysis: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Add error notice to analysis."""
        analysis = analysis.copy()
        analysis["ai_available"] = False
        analysis["ai_error"] = f"AI analysis error: {error}"
        return analysis


# Singleton instance for global use
_ai_analyzer_instance = None

def get_ai_burnout_analyzer() -> AIBurnoutAnalyzerService:
    """Get singleton instance of AI burnout analyzer."""
    global _ai_analyzer_instance
    if _ai_analyzer_instance is None:
        _ai_analyzer_instance = AIBurnoutAnalyzerService()
    return _ai_analyzer_instance