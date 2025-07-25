"""
Simplified burnout analysis engine for web API integration.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SimpleBurnoutAnalyzer:
    """Simplified burnout analyzer focused on incident data."""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        # Initialize the client attribute to fix missing client error
        self.client = None
        # Default thresholds for risk assessment
        self.thresholds = {
            "incidents_per_week_high": 8,
            "incidents_per_week_medium": 4,
            "after_hours_percentage_high": 0.3,
            "after_hours_percentage_medium": 0.15,
            "avg_resolution_hours_high": 6,
            "avg_resolution_hours_medium": 3,
        }
    
    async def analyze_burnout(
        self, 
        time_range_days: int = 30,
        include_weekends: bool = True,
        include_github: bool = False,
        include_slack: bool = False,
        github_token: str = None,
        slack_token: str = None
    ) -> Dict[str, Any]:
        """
        Analyze burnout for the team based on incident data.
        This is the simplified version without AI enhancement.
        """
        from ..core.rootly_client import RootlyAPIClient
        
        logger.info(f"Starting simplified burnout analysis for {time_range_days} days")
        
        # Initialize Rootly API client and store it for error handling
        self.client = RootlyAPIClient(self.api_token)
        
        # Collect data from Rootly
        rootly_data = await self.client.collect_analysis_data(time_range_days)
        
        # Process the data using the existing team analysis method
        result = self.analyze_team_burnout(
            users=rootly_data.get("users", []),
            incidents=rootly_data.get("incidents", []),
            metadata=rootly_data.get("collection_metadata", {})
        )
        
        return result
    
    def analyze_team_burnout(
        self, 
        users: List[Dict[str, Any]], 
        incidents: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze burnout risk for entire team."""
        # Handle None inputs safely
        users = users or []
        incidents = incidents or []
        metadata = metadata or {}
        
        logger.info(f"Starting team burnout analysis for {len(users)} users and {len(incidents)} incidents")
        
        # Process incidents to extract user involvement
        user_incident_mapping = self._map_users_to_incidents(users, incidents)
        
        # Analyze each user
        team_analysis = []
        for user in users:
            if not user or not isinstance(user, dict):
                logger.warning("Skipping invalid user data (not a dict)")
                continue
                
            user_id = user.get("id")
            if user_id:
                try:
                    user_incidents = [
                        inc for inc in incidents 
                        if inc and isinstance(inc, dict) and user_id in user_incident_mapping.get(str(user_id), [])
                    ]
                    
                    user_analysis = self._analyze_user_burnout(user, user_incidents, metadata)
                    if user_analysis:
                        team_analysis.append(user_analysis)
                except Exception as e:
                    logger.warning(f"Error analyzing user {user_id}: {e}")
                    continue
        
        # Calculate team summary
        team_summary = self._calculate_team_summary(team_analysis)
        
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "metadata": metadata,
            "team_summary": team_summary,
            "team_analysis": team_analysis,
            "recommendations": self._generate_team_recommendations(team_summary, team_analysis),
            "ai_enhanced": False
        }
    
    def _analyze_user_burnout(
        self, 
        user: Dict[str, Any], 
        user_incidents: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze burnout risk for a single user."""
        user_attrs = user.get("attributes", {})
        user_id = user.get("id")
        user_name = user_attrs.get("full_name") or user_attrs.get("name", "Unknown")
        user_email = user_attrs.get("email")
        
        if not user_incidents:
            return {
                "user_id": user_id,
                "user_name": user_name,
                "user_email": user_email,
                "burnout_score": 0.0,
                "risk_level": "low",
                "incident_count": 0,
                "key_metrics": {
                    "incidents_per_week": 0,
                    "after_hours_percentage": 0,
                    "avg_resolution_hours": 0
                },
                "recommendations": ["No recent incident involvement - maintaining good work-life balance"]
            }
        
        # Calculate key metrics
        days_analyzed = metadata.get("days_analyzed", 30)
        incidents_per_week = (len(user_incidents) / days_analyzed) * 7
        
        # Calculate after-hours percentage (simple version - weekends + outside 9-17)
        after_hours_count = self._count_after_hours_incidents(user_incidents)
        after_hours_percentage = after_hours_count / len(user_incidents) if user_incidents else 0
        
        # Calculate average resolution time
        resolution_times = []
        for incident in user_incidents:
            duration = self._extract_incident_duration(incident)
            if duration:
                resolution_times.append(duration)
        
        avg_resolution_hours = (
            sum(resolution_times) / len(resolution_times) / 60 
            if resolution_times else 0
        )
        
        # Calculate burnout score (0-10 scale)
        frequency_score = min(10, (incidents_per_week / self.thresholds["incidents_per_week_high"]) * 10)
        after_hours_score = min(10, (after_hours_percentage / self.thresholds["after_hours_percentage_high"]) * 10)
        duration_score = min(10, (avg_resolution_hours / self.thresholds["avg_resolution_hours_high"]) * 10)
        
        # Weight the scores (frequency is most important)
        burnout_score = (frequency_score * 0.5) + (after_hours_score * 0.3) + (duration_score * 0.2)
        
        # Determine risk level
        risk_level = self._determine_risk_level(burnout_score)
        
        # Generate recommendations
        recommendations = self._generate_user_recommendations(
            incidents_per_week, after_hours_percentage, avg_resolution_hours, risk_level
        )
        
        return {
            "user_id": user_id,
            "user_name": user_name,
            "user_email": user_email,
            "burnout_score": round(burnout_score, 2),
            "risk_level": risk_level,
            "incident_count": len(user_incidents),
            "key_metrics": {
                "incidents_per_week": round(incidents_per_week, 2),
                "after_hours_percentage": round(after_hours_percentage * 100, 1),
                "avg_resolution_hours": round(avg_resolution_hours, 2)
            },
            "recommendations": recommendations
        }
    
    def _map_users_to_incidents(
        self, 
        users: List[Dict[str, Any]], 
        incidents: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Map users to incidents they were involved in."""
        user_incidents = {}
        
        for incident in incidents:
            if not incident or not isinstance(incident, dict):
                continue
                
            incident_id = incident.get("id")
            if not incident_id:
                continue
                
            attrs = incident.get("attributes", {})
            if not isinstance(attrs, dict):
                continue
            
            # Extract user involvement from various fields
            involved_users = set()
            
            try:
                # Created by
                user_data = attrs.get("user", {})
                if isinstance(user_data, dict) and user_data.get("data", {}).get("id"):
                    involved_users.add(str(user_data["data"]["id"]))
                
                # Started by
                started_by_data = attrs.get("started_by", {})
                if isinstance(started_by_data, dict) and started_by_data.get("data", {}).get("id"):
                    involved_users.add(str(started_by_data["data"]["id"]))
                
                # Resolved by
                resolved_by_data = attrs.get("resolved_by", {})
                if isinstance(resolved_by_data, dict) and resolved_by_data.get("data", {}).get("id"):
                    involved_users.add(str(resolved_by_data["data"]["id"]))
                
                # Add incident to each involved user
                for user_id in involved_users:
                    if user_id not in user_incidents:
                        user_incidents[user_id] = []
                    user_incidents[user_id].append(incident_id)
                    
            except Exception as e:
                logger.warning(f"Error processing incident {incident_id}: {e}")
                continue
        
        return user_incidents
    
    def _count_after_hours_incidents(self, incidents: List[Dict[str, Any]]) -> int:
        """Count incidents that occurred outside business hours."""
        after_hours_count = 0
        
        for incident in incidents:
            created_at = incident.get("attributes", {}).get("created_at")
            if created_at:
                try:
                    # Parse ISO format timestamp
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    # Check if weekend (Saturday=5, Sunday=6)
                    is_weekend = dt.weekday() >= 5
                    
                    # Check if outside business hours (9 AM - 5 PM)
                    is_after_hours = dt.hour < 9 or dt.hour >= 17
                    
                    if is_weekend or is_after_hours:
                        after_hours_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error parsing timestamp {created_at}: {e}")
        
        return after_hours_count
    
    def _extract_incident_duration(self, incident: Dict[str, Any]) -> Optional[float]:
        """Extract incident duration in minutes."""
        attrs = incident.get("attributes", {})
        started_at = attrs.get("started_at")
        resolved_at = attrs.get("resolved_at")
        
        if not started_at or not resolved_at:
            return None
        
        try:
            start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            end = datetime.fromisoformat(resolved_at.replace('Z', '+00:00'))
            return (end - start).total_seconds() / 60
        except Exception as e:
            logger.warning(f"Error calculating duration: {e}")
            return None
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on burnout score."""
        if score >= 7:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"
    
    def _generate_user_recommendations(
        self, 
        incidents_per_week: float, 
        after_hours_percentage: float, 
        avg_resolution_hours: float,
        risk_level: str
    ) -> List[str]:
        """Generate personalized recommendations."""
        recommendations = []
        
        if risk_level == "high":
            recommendations.append("⚠️ High burnout risk detected - consider workload redistribution")
        
        if incidents_per_week > self.thresholds["incidents_per_week_medium"]:
            recommendations.append(f"📊 High incident volume ({incidents_per_week:.1f}/week) - review on-call rotations")
        
        if after_hours_percentage > self.thresholds["after_hours_percentage_medium"]:
            recommendations.append(f"🌙 High after-hours activity ({after_hours_percentage*100:.1f}%) - establish boundaries")
        
        if avg_resolution_hours > self.thresholds["avg_resolution_hours_medium"]:
            recommendations.append(f"⏱️ Long resolution times ({avg_resolution_hours:.1f}h avg) - review processes")
        
        if risk_level == "low":
            recommendations.append("✅ Healthy incident involvement - maintaining good balance")
        
        return recommendations or ["No specific recommendations at this time"]
    
    def _calculate_team_summary(self, team_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate team-wide summary statistics."""
        if not team_analysis:
            return {}
        
        scores = [user["burnout_score"] for user in team_analysis]
        risk_counts = {"high": 0, "medium": 0, "low": 0}
        
        for user in team_analysis:
            risk_counts[user["risk_level"]] += 1
        
        return {
            "total_users": len(team_analysis),
            "average_score": round(sum(scores) / len(scores), 2),
            "highest_score": max(scores),
            "risk_distribution": risk_counts,
            "users_at_risk": risk_counts["high"] + risk_counts["medium"]
        }
    
    def _generate_team_recommendations(
        self, 
        team_summary: Dict[str, Any], 
        team_analysis: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate team-level recommendations."""
        recommendations = []
        
        high_risk_count = team_summary.get("risk_distribution", {}).get("high", 0)
        medium_risk_count = team_summary.get("risk_distribution", {}).get("medium", 0)
        total_users = team_summary.get("total_users", 0)
        
        if high_risk_count > 0:
            recommendations.append(f"🚨 {high_risk_count} team members at high burnout risk - immediate attention needed")
        
        if total_users > 0 and (high_risk_count + medium_risk_count) / total_users > 0.5:
            recommendations.append("📋 Consider team workload redistribution and process improvements")
        
        avg_score = team_summary.get("average_score", 0)
        if avg_score > 6:
            recommendations.append("⚖️ Team average burnout score is high - review on-call policies")
        elif avg_score < 3:
            recommendations.append("✅ Team burnout levels are healthy - maintain current practices")
        
        return recommendations or ["Team analysis completed - review individual recommendations"]