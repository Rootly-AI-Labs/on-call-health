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
            
            # Log AI enhancement details before merging
            traditional_member_count = len(traditional_analysis.get('members', []))
            ai_enhanced_count = len([m for m in ai_insights.get('members', []) if m.get('ai_insights')])
            self.logger.info(f"AI Enhancement Summary - Traditional members: {traditional_member_count}, AI enhanced: {ai_enhanced_count}")
            
            # Merge AI insights with traditional analysis
            enhanced_analysis = self._merge_analyses(traditional_analysis, ai_insights)
            
            # Log final enhancement results
            final_member_count = len(enhanced_analysis.get('members', []))
            ai_enabled_final = enhanced_analysis.get('ai_enhanced', False)
            self.logger.info(f"AI Enhancement Complete - Final members: {final_member_count}, AI enabled: {ai_enabled_final}")
            
            return enhanced_analysis
            
        except Exception as e:
            self.logger.error(f"Error in AI analysis enhancement: {e}")
            self.logger.error(f"AI Enhancement Error Details - Traditional analysis size: {len(traditional_analysis.get('members', []))}, Error type: {type(e).__name__}")
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
            # Analyze team patterns with verbose insights
            team_insights = {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "team_size": len(team_members),
                "data_sources": available_integrations,
                "executive_summary": self._generate_executive_summary(team_members, available_integrations),
                "risk_distribution": self._analyze_team_risk_distribution(team_members),
                "detailed_risk_analysis": self._generate_detailed_risk_analysis(team_members),
                "common_patterns": self._identify_common_patterns(team_members),
                "burnout_indicators": self._analyze_burnout_indicators(team_members),
                "workload_distribution": self._analyze_workload_distribution(team_members),
                "communication_analysis": self._analyze_team_communication(team_members),
                "temporal_patterns": self._analyze_temporal_patterns(team_members),
                "team_recommendations": self._generate_team_recommendations(team_members),
                "individual_insights": self._generate_individual_member_insights(team_members),
                "trend_analysis": self._analyze_team_trends(team_members),
                "risk_factors": self._identify_primary_risk_factors(team_members)
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
        risk_members = {"low": [], "medium": [], "high": [], "critical": []}
        ai_escalations = 0
        
        for member in team_members:
            try:
                if not member or not isinstance(member, dict):
                    logger.debug("Skipping invalid member in team enhancement")
                    continue
                    
                # Safe extraction of member data
                risk_level = "low"
                member_name = "Unknown"
                member_email = ""
                
                try:
                    raw_risk_level = member.get("risk_level", "low")
                    if isinstance(raw_risk_level, str):
                        risk_level = raw_risk_level.lower()
                except Exception as e:
                    logger.debug(f"Error extracting risk_level: {e}")
                    
                try:
                    raw_member_name = member.get("user_name", "Unknown")
                    if isinstance(raw_member_name, str):
                        member_name = raw_member_name
                except Exception as e:
                    logger.debug(f"Error extracting user_name: {e}")
                    
                try:
                    raw_member_email = member.get("user_email", "")
                    if isinstance(raw_member_email, str):
                        member_email = raw_member_email
                except Exception as e:
                    logger.debug(f"Error extracting user_email: {e}")
            except Exception as e:
                logger.warning(f"Error processing member in team enhancement: {e}")
                continue
            
            if risk_level in risk_counts:
                risk_counts[risk_level] += 1
                risk_members[risk_level].append({
                    "name": member_name,
                    "email": member_email,
                    "user_id": member.get("user_id"),
                    "burnout_score": member.get("burnout_score", 0),
                    "incident_count": len(member.get("incidents", []))
                })
            
            if member.get("risk_escalated_by_ai"):
                ai_escalations += 1
        
        total = len(team_members)
        high_risk_count = risk_counts["high"] + risk_counts["critical"]
        
        return {
            "distribution": risk_counts,
            "members_by_risk": risk_members,
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
        high_risk_members = risk_dist["members_by_risk"]["high"] + risk_dist["members_by_risk"]["critical"]
        medium_risk_members = risk_dist["members_by_risk"]["medium"]
        
        if high_risk_pct > 30:
            high_risk_names = [member["name"] for member in high_risk_members]
            recommendations.append({
                "priority": "urgent",
                "category": "team_health",
                "title": "Team Burnout Risk Critical",
                "description": f"{high_risk_pct:.1f}% of team members show high burnout risk",
                "at_risk_members": high_risk_names,
                "member_details": high_risk_members,
                "actions": [
                    f"Conduct immediate workload review for: {', '.join(high_risk_names)}" if high_risk_names else "Conduct immediate team workload review",
                    "Implement team-wide stress reduction measures",
                    "Consider bringing in additional resources",
                    "Review team processes and efficiency"
                ]
            })
        elif high_risk_pct > 15:
            elevated_risk_members = high_risk_members + medium_risk_members
            elevated_risk_names = [member["name"] for member in elevated_risk_members]
            recommendations.append({
                "priority": "high",
                "category": "team_health", 
                "title": "Team Burnout Prevention",
                "description": f"{high_risk_pct:.1f}% of team members show elevated burnout risk",
                "at_risk_members": elevated_risk_names,
                "member_details": elevated_risk_members,
                "actions": [
                    f"Monitor workload trends for: {', '.join(elevated_risk_names)}" if elevated_risk_names else "Monitor team workload trends closely",
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


    def _generate_executive_summary(self, team_members: List[Dict[str, Any]], available_integrations: List[str]) -> Dict[str, Any]:
        """Generate a comprehensive executive summary of team burnout status."""
        risk_dist = self._analyze_team_risk_distribution(team_members)
        total_incidents = sum(len(member.get("incidents", [])) for member in team_members)
        avg_burnout_score = sum(member.get("burnout_score", 0) for member in team_members) / len(team_members) if team_members else 0
        
        high_risk_count = risk_dist["distribution"]["high"] + risk_dist["distribution"]["critical"]
        medium_risk_count = risk_dist["distribution"]["medium"]
        
        # Generate narrative summary
        if high_risk_count > 0:
            urgency_level = "Critical"
            primary_concern = f"{high_risk_count} team member(s) showing severe burnout symptoms requiring immediate intervention"
        elif medium_risk_count > len(team_members) * 0.5:
            urgency_level = "High"
            primary_concern = f"Over half the team ({medium_risk_count} members) showing elevated stress levels"
        elif medium_risk_count > 0:
            urgency_level = "Moderate"
            primary_concern = f"{medium_risk_count} team member(s) showing early burnout warning signs"
        else:
            urgency_level = "Low"
            primary_concern = "Team appears to be managing workload effectively"
        
        return {
            "urgency_level": urgency_level,
            "overall_health_score": round(100 - (avg_burnout_score * 10), 1),
            "primary_concern": primary_concern,
            "key_metrics": {
                "total_team_incidents": total_incidents,
                "average_burnout_score": round(avg_burnout_score, 2),
                "high_risk_percentage": risk_dist["high_risk_percentage"],
                "data_completeness": len(available_integrations)
            },
            "immediate_actions_needed": high_risk_count > 0,
            "team_trajectory": "Declining" if avg_burnout_score > 5 else "Stable" if avg_burnout_score > 3 else "Healthy"
        }
    
    def _generate_detailed_risk_analysis(self, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate detailed analysis of risk factors across the team."""
        detailed_analysis = {
            "risk_breakdown": {},
            "contributing_factors": [],
            "member_spotlight": []
        }
        
        for risk_level in ["critical", "high", "medium", "low"]:
            members_at_risk = []
            try:
                for m in team_members:
                    if m and isinstance(m, dict):
                        try:
                            member_risk_level = m.get("risk_level", "low")
                            if isinstance(member_risk_level, str) and member_risk_level.lower() == risk_level:
                                members_at_risk.append(m)
                        except Exception as e:
                            logger.debug(f"Error checking risk level for member: {e}")
                            continue
            except Exception as e:
                logger.warning(f"Error processing risk level {risk_level}: {e}")
                members_at_risk = []
            if members_at_risk:
                detailed_analysis["risk_breakdown"][risk_level] = {
                    "count": len(members_at_risk),
                    "members": [m.get("user_name", "Unknown") for m in members_at_risk],
                    "common_patterns": self._identify_risk_patterns(members_at_risk),
                    "severity_indicators": self._get_severity_indicators(members_at_risk)
                }
        
        # Identify top contributing factors
        all_factors = []
        for member in team_members:
            ai_insights = member.get("ai_insights", {})
            if ai_insights and ai_insights.get("insights"):
                factors = ai_insights["insights"].get("primary_risk_factors", [])
                all_factors.extend(factors)
        
        from collections import Counter
        factor_counts = Counter(all_factors)
        detailed_analysis["contributing_factors"] = [
            {"factor": factor, "affected_members": count, "percentage": round(count/len(team_members)*100, 1)}
            for factor, count in factor_counts.most_common(5)
        ]
        
        return detailed_analysis
    
    def _analyze_burnout_indicators(self, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze specific burnout indicators across the team."""
        indicators = {
            "emotional_exhaustion": {"severe": 0, "moderate": 0, "mild": 0},
            "depersonalization": {"severe": 0, "moderate": 0, "mild": 0},
            "reduced_accomplishment": {"severe": 0, "moderate": 0, "mild": 0},
            "after_hours_activity": {"concerning": [], "moderate": [], "normal": []},
            "communication_stress": {"high": [], "moderate": [], "low": []},
            "workload_sustainability": {"unsustainable": [], "concerning": [], "manageable": []}
        }
        
        for member in team_members:
            name = member.get("user_name", "Unknown")
            ai_insights = member.get("ai_insights", {})
            
            # Analyze Maslach dimensions if available
            maslach = ai_insights.get("maslach_analysis", {}) if ai_insights else {}
            
            # After-hours analysis
            after_hours_pct = member.get("after_hours_percentage", 0)
            if after_hours_pct > 40:
                indicators["after_hours_activity"]["concerning"].append({
                    "name": name, "percentage": after_hours_pct
                })
            elif after_hours_pct > 20:
                indicators["after_hours_activity"]["moderate"].append({
                    "name": name, "percentage": after_hours_pct
                })
            else:
                indicators["after_hours_activity"]["normal"].append({
                    "name": name, "percentage": after_hours_pct
                })
        
        return indicators
    
    def _analyze_team_communication(self, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze team communication patterns and stress indicators."""
        communication_analysis = {
            "overall_sentiment": "neutral",
            "stress_indicators": [],
            "communication_volume": {"high": [], "normal": [], "low": []},
            "negative_sentiment_trends": [],
            "team_interaction_health": "unknown"
        }
        
        total_messages = 0
        sentiment_scores = []
        
        for member in team_members:
            name = member.get("user_name", "Unknown")
            ai_insights = member.get("ai_insights", {})
            
            if ai_insights and "sentiment_analysis" in ai_insights:
                sentiment = ai_insights["sentiment_analysis"]
                sentiment_score = sentiment.get("sentiment_score", 0)
                message_count = sentiment.get("total_messages", 0)
                
                sentiment_scores.append(sentiment_score)
                total_messages += message_count
                
                if sentiment_score < -0.3:
                    communication_analysis["negative_sentiment_trends"].append({
                        "member": name,
                        "sentiment_score": sentiment_score,
                        "stress_indicators": sentiment.get("stress_indicators", [])
                    })
        
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            communication_analysis["overall_sentiment"] = (
                "negative" if avg_sentiment < -0.1 else 
                "neutral" if avg_sentiment < 0.1 else 
                "positive"
            )
            communication_analysis["team_sentiment_score"] = round(avg_sentiment, 3)
        
        return communication_analysis
    
    def _analyze_temporal_patterns(self, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal work patterns across the team."""
        patterns = {
            "peak_activity_hours": {},
            "weekend_work_analysis": {},
            "after_hours_trends": {},
            "burnout_progression": []
        }
        
        # Aggregate temporal data
        all_hours = []
        weekend_workers = []
        after_hours_workers = []
        
        for member in team_members:
            name = member.get("user_name", "Unknown")
            
            # Weekend work analysis
            weekend_pct = member.get("weekend_percentage", 0)
            if weekend_pct > 15:
                weekend_workers.append({"name": name, "percentage": weekend_pct})
            
            # After hours analysis
            after_hours_pct = member.get("after_hours_percentage", 0)
            if after_hours_pct > 25:
                after_hours_workers.append({"name": name, "percentage": after_hours_pct})
        
        patterns["weekend_work_analysis"] = {
            "members_working_weekends": weekend_workers,
            "team_weekend_work_rate": len(weekend_workers) / len(team_members) * 100 if team_members else 0
        }
        
        patterns["after_hours_trends"] = {
            "members_working_after_hours": after_hours_workers,
            "team_after_hours_rate": len(after_hours_workers) / len(team_members) * 100 if team_members else 0
        }
        
        return patterns
    
    def _generate_individual_member_insights(self, team_members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate detailed insights for each team member."""
        individual_insights = []
        
        for member in team_members:
            name = member.get("user_name", "Unknown")
            risk_level = member.get("risk_level", "low")
            burnout_score = member.get("burnout_score", 0)
            incident_count = len(member.get("incidents", []))
            
            ai_insights = member.get("ai_insights", {})
            member_insight = {
                "name": name,
                "risk_level": risk_level,
                "burnout_score": burnout_score,
                "incident_load": incident_count,
                "key_concerns": [],
                "strengths": [],
                "recommended_actions": [],
                "manager_notes": ""
            }
            
            # Extract key insights from AI analysis
            if ai_insights and ai_insights.get("insights"):
                insights = ai_insights["insights"]
                member_insight["key_concerns"] = insights.get("primary_risk_factors", [])
                member_insight["recommended_actions"] = insights.get("recommendations", [])
                
                # Generate manager notes
                if risk_level.lower() in ["high", "critical"]:
                    member_insight["manager_notes"] = f"Immediate attention required for {name}. Schedule 1:1 to discuss workload and stress levels."
                elif risk_level.lower() == "medium":
                    member_insight["manager_notes"] = f"Monitor {name} closely. Consider preventive measures to avoid escalation."
                else:
                    member_insight["manager_notes"] = f"{name} appears to be managing well. Continue current support level."
            
            individual_insights.append(member_insight)
        
        return individual_insights
    
    def _analyze_team_trends(self, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends and patterns in team burnout risk."""
        trends = {
            "risk_trajectory": "stable",
            "emerging_patterns": [],
            "early_warning_signs": [],
            "positive_indicators": [],
            "team_resilience_factors": []
        }
        
        # Count high-risk members with null safety
        high_risk_count = 0
        try:
            for m in team_members:
                if m and isinstance(m, dict):
                    try:
                        risk_level = m.get("risk_level", "low")
                        if isinstance(risk_level, str) and risk_level.lower() in ["high", "critical"]:
                            high_risk_count += 1
                    except Exception as e:
                        logger.debug(f"Error checking high risk level for member: {e}")
                        continue
        except Exception as e:
            logger.warning(f"Error counting high-risk members: {e}")
            high_risk_count = 0
        total_members = len(team_members)
        
        if high_risk_count > total_members * 0.5:
            trends["risk_trajectory"] = "rapidly_declining"
            trends["early_warning_signs"].append("Over 50% of team showing high burnout risk")
        elif high_risk_count > total_members * 0.3:
            trends["risk_trajectory"] = "concerning"
            trends["early_warning_signs"].append("Significant portion of team under stress")
        
        # Identify positive indicators with null safety
        low_risk_count = 0
        try:
            for m in team_members:
                if m and isinstance(m, dict):
                    try:
                        risk_level = m.get("risk_level", "low")
                        if isinstance(risk_level, str) and risk_level.lower() == "low":
                            low_risk_count += 1
                    except Exception as e:
                        logger.debug(f"Error checking low risk level for member: {e}")
                        continue
        except Exception as e:
            logger.warning(f"Error counting low-risk members: {e}")
            low_risk_count = 0
        if low_risk_count > total_members * 0.6:
            trends["positive_indicators"].append("Majority of team showing healthy stress levels")
        
        return trends
    
    def _identify_primary_risk_factors(self, team_members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify and rank primary risk factors affecting the team."""
        risk_factors = []
        
        # Analyze workload factors
        high_incident_members = [m for m in team_members if len(m.get("incidents", [])) > 10]
        if high_incident_members:
            risk_factors.append({
                "factor": "Excessive Incident Load",
                "severity": "high" if len(high_incident_members) > len(team_members) * 0.3 else "medium",
                "affected_members": [m.get("user_name", "Unknown") for m in high_incident_members],
                "description": f"{len(high_incident_members)} team members handling excessive incident volumes",
                "recommended_action": "Redistribute incident load and review escalation procedures"
            })
        
        # Analyze temporal factors
        after_hours_members = [m for m in team_members if m.get("after_hours_percentage", 0) > 30]
        if after_hours_members:
            risk_factors.append({
                "factor": "After-Hours Work Overload",
                "severity": "high" if len(after_hours_members) > len(team_members) * 0.4 else "medium",
                "affected_members": [m.get("user_name", "Unknown") for m in after_hours_members],
                "description": f"{len(after_hours_members)} team members regularly working after hours",
                "recommended_action": "Implement after-hours work policies and improve coverage rotation"
            })
        
        return risk_factors
    
    def _identify_risk_patterns(self, members_at_risk: List[Dict[str, Any]]) -> List[str]:
        """Identify common patterns among members at the same risk level."""
        patterns = []
        
        high_incident_count = len([m for m in members_at_risk if len(m.get("incidents", [])) > 8])
        if high_incident_count > len(members_at_risk) * 0.5:
            patterns.append("High incident load")
        
        after_hours_count = len([m for m in members_at_risk if m.get("after_hours_percentage", 0) > 25])
        if after_hours_count > len(members_at_risk) * 0.5:
            patterns.append("Excessive after-hours work")
        
        return patterns
    
    def _get_severity_indicators(self, members_at_risk: List[Dict[str, Any]]) -> List[str]:
        """Get severity indicators for members at risk."""
        indicators = []
        
        avg_burnout = sum(m.get("burnout_score", 0) for m in members_at_risk) / len(members_at_risk)
        if avg_burnout > 7:
            indicators.append("Severe burnout scores")
        
        total_incidents = sum(len(m.get("incidents", [])) for m in members_at_risk)
        if total_incidents > len(members_at_risk) * 15:
            indicators.append("Overwhelming incident volume")
        
        return indicators


# Singleton instance for global use
_ai_analyzer_instance = None

def get_ai_burnout_analyzer() -> AIBurnoutAnalyzerService:
    """Get singleton instance of AI burnout analyzer."""
    global _ai_analyzer_instance
    if _ai_analyzer_instance is None:
        _ai_analyzer_instance = AIBurnoutAnalyzerService()
    return _ai_analyzer_instance