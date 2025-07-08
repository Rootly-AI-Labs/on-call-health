"""
PagerDuty Burnout Analyzer Service

Analyzes burnout risk factors using PagerDuty incident and user data.
Uses the same calculation methodology as Rootly for consistent results.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from app.core.pagerduty_client import PagerDutyAPIClient

logger = logging.getLogger(__name__)

class PagerDutyBurnoutAnalyzerService:
    """
    Service for analyzing burnout risk factors using PagerDuty data.
    Follows the same methodology as RootlyBurnoutAnalyzerService for consistency.
    """
    
    def __init__(self, api_token: str):
        self.client = PagerDutyAPIClient(api_token)
    
    async def analyze_burnout(
        self, 
        time_range_days: int = 30,
        include_weekends: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze burnout for the team based on PagerDuty incident data.
        
        Returns structured analysis results with:
        - Overall team health score
        - Individual member burnout scores
        - Burnout factors
        """
        logger.info(f"Starting PagerDuty burnout analysis for {time_range_days} days")
        
        try:
            # Fetch data from PagerDuty
            logger.info(f"TRACE: About to call _fetch_analysis_data for {time_range_days} days")
            data = await self._fetch_analysis_data(time_range_days)
            logger.info(f"TRACE: _fetch_analysis_data returned: type={type(data)}, is_none={data is None}")
            
            # Check if data was successfully fetched
            if data is None:
                logger.error("TRACE: Data is None after _fetch_analysis_data")
                raise Exception("Failed to fetch data from PagerDuty API - no data returned")
            
            # Extract users and incidents
            logger.info(f"TRACE: About to extract users and incidents from data")
            users = data.get("users", []) if data else []
            incidents = data.get("incidents", []) if data else []
            metadata = data.get("collection_metadata", {}) if data else {}
            logger.info(f"TRACE: Extracted {len(users)} users, {len(incidents)} incidents")
            
            # Analyze team burnout
            try:
                logger.info(f"TRACE: About to call _analyze_team_data with {len(users)} users, {len(incidents)} incidents")
                team_analysis = self._analyze_team_data(
                    users, 
                    incidents, 
                    metadata,
                    include_weekends
                )
                logger.info(f"TRACE: _analyze_team_data completed successfully")
            except Exception as e:
                logger.error(f"TRACE: Error in _analyze_team_data: {e}")
                logger.error(f"TRACE: Users data type: {type(users)}, length: {len(users) if users else 'N/A'}")
                logger.error(f"TRACE: Incidents data type: {type(incidents)}, length: {len(incidents) if incidents else 'N/A'}")
                logger.error(f"TRACE: Metadata data type: {type(metadata)}")
                raise
            
            # Calculate overall team health
            team_health = self._calculate_team_health(team_analysis["members"])
            
            # Generate insights and recommendations
            insights = self._generate_insights(team_analysis, team_health)
            
            return {
                "analysis_timestamp": datetime.now().isoformat(),
                "metadata": {
                    **metadata,
                    "include_weekends": include_weekends
                },
                "team_health": team_health,
                "team_analysis": team_analysis,
                "insights": insights,
                "recommendations": self._generate_recommendations(team_health, team_analysis)
            }
            
        except Exception as e:
            logger.error(f"PagerDuty burnout analysis failed: {e}")
            raise
    
    async def _fetch_analysis_data(self, days_back: int) -> Dict[str, Any]:
        """Fetch all required data from PagerDuty API."""
        try:
            logger.info(f"Fetching PagerDuty analysis data for {days_back} days")
            data = await self.client.collect_analysis_data(days_back=days_back)
            
            # Add detailed logging to debug the NoneType issue
            logger.info(f"Collect analysis data returned: {type(data)}")
            if data:
                logger.info(f"Data keys: {list(data.keys())}")
                logger.info(f"Users count: {len(data.get('users', []))}")
                logger.info(f"Incidents count: {len(data.get('incidents', []))}")
            else:
                logger.error("collect_analysis_data returned None or empty")
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch PagerDuty analysis data: {e}")
            raise
    
    def _analyze_team_data(
        self, 
        users: List[Dict[str, Any]], 
        incidents: List[Dict[str, Any]], 
        metadata: Dict[str, Any],
        include_weekends: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze team data and calculate burnout metrics for each member.
        Uses the same methodology as Rootly analysis for consistency.
        """
        logger.info(f"Analyzing PagerDuty team data: {len(users)} users, {len(incidents)} incidents")
        
        # Convert PagerDuty data to common format
        normalized_incidents = self._normalize_pagerduty_incidents(incidents)
        normalized_users = self._normalize_pagerduty_users(users)
        
        # Calculate individual member metrics using the same logic as Rootly
        member_analyses = []
        
        for user in normalized_users:
            try:
                user_id = user["id"]
                user_name = user["name"]
                user_email = user["email"]
                
                # Filter incidents for this user
                user_incidents = [
                    incident for incident in normalized_incidents 
                    if self._is_user_involved_in_incident(user_id, incident)
                ]
                
                # Calculate burnout metrics using same methodology as Rootly
                metrics = self._calculate_user_burnout_metrics(
                    user_incidents, 
                    metadata.get("days_analyzed", 30),
                    include_weekends
                )
                
                # Calculate burnout factors
                factors = self._calculate_burnout_factors(metrics, user_incidents)
                
                # Calculate overall burnout score (0-1 scale)
                burnout_score = self._calculate_overall_burnout_score(factors)
                
                # Determine risk level
                risk_level = self._determine_risk_level(burnout_score)
                
                member_analyses.append({
                    "user_id": user_id,
                    "user_name": user_name,
                    "user_email": user_email,
                    "incident_count": len(user_incidents),
                    "burnout_score": burnout_score,
                    "risk_level": risk_level,
                    "factors": factors,
                    "metrics": metrics
                })
                
            except Exception as e:
                logger.error(f"Error analyzing user {user.get('name', 'Unknown')}: {e}")
                # Continue with other users
                continue
        
        return {
            "members": member_analyses,
            "total_incidents": len(normalized_incidents),
            "analysis_period_days": metadata.get("days_analyzed", 30),
            "weekend_analysis_enabled": include_weekends
        }
    
    def _normalize_pagerduty_incidents(self, incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert PagerDuty incidents to common format used by Rootly analyzer."""
        normalized = []
        
        for incident in incidents:
            try:
                # Extract basic incident info
                incident_id = incident.get("id", "")
                title = incident.get("title", "")
                status = incident.get("status", "")
                
                # Parse timestamps
                created_at = self._parse_pagerduty_timestamp(incident.get("created_at"))
                updated_at = self._parse_pagerduty_timestamp(incident.get("last_status_change_at"))
                
                # Extract user assignments from incident
                assigned_users = []
                
                # Get users from assignments
                assignments = incident.get("assignments", [])
                for assignment in assignments:
                    assignee = assignment.get("assignee", {})
                    if assignee.get("type") == "user_reference":
                        assigned_users.append({
                            "id": assignee.get("id", ""),
                            "name": assignee.get("summary", ""),
                            "email": assignee.get("email", "")
                        })
                
                # Get service info
                service = incident.get("service", {})
                service_name = service.get("summary", "Unknown Service")
                
                # Calculate resolution time if resolved
                resolution_time_minutes = None
                if status == "resolved" and created_at and updated_at:
                    resolution_time_minutes = (updated_at - created_at).total_seconds() / 60
                
                normalized_incident = {
                    "id": incident_id,
                    "title": title,
                    "status": status,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "resolution_time_minutes": resolution_time_minutes,
                    "service_name": service_name,
                    "assigned_users": assigned_users,
                    "severity": self._map_pagerduty_severity(incident),
                    "original_data": incident  # Keep original for reference
                }
                
                normalized.append(normalized_incident)
                
            except Exception as e:
                logger.error(f"Error normalizing PagerDuty incident {incident.get('id', 'unknown')}: {e}")
                continue
        
        return normalized
    
    def _normalize_pagerduty_users(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert PagerDuty users to common format."""
        normalized = []
        
        for user in users:
            try:
                user_id = user.get("id", "")
                name = user.get("name", "")
                email = user.get("email", "")
                
                # Get contact methods
                contact_methods = user.get("contact_methods", [])
                
                # Get team memberships
                teams = user.get("teams", [])
                team_names = [team.get("summary", "") for team in teams]
                
                normalized_user = {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "teams": team_names,
                    "contact_methods": contact_methods,
                    "original_data": user
                }
                
                normalized.append(normalized_user)
                
            except Exception as e:
                logger.error(f"Error normalizing PagerDuty user {user.get('name', 'unknown')}: {e}")
                continue
        
        return normalized
    
    def _parse_pagerduty_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse PagerDuty timestamp string to datetime object."""
        if not timestamp_str:
            return None
        
        try:
            # PagerDuty uses ISO 8601 format
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.error(f"Error parsing timestamp {timestamp_str}: {e}")
            return None
    
    def _map_pagerduty_severity(self, incident: Dict[str, Any]) -> str:
        """Map PagerDuty incident to severity level."""
        # PagerDuty doesn't have built-in severity, so we use urgency and priority
        urgency = incident.get("urgency", "low")
        priority = incident.get("priority", {})
        
        if priority:
            priority_name = priority.get("name", "").lower()
            if "p1" in priority_name or "critical" in priority_name:
                return "critical"
            elif "p2" in priority_name or "high" in priority_name:
                return "high"
            elif "p3" in priority_name or "medium" in priority_name:
                return "medium"
        
        # Fall back to urgency
        if urgency == "high":
            return "high"
        else:
            return "low"
    
    def _is_user_involved_in_incident(self, user_id: str, incident: Dict[str, Any]) -> bool:
        """Check if a user was involved in handling an incident."""
        # Check assigned users
        assigned_users = incident.get("assigned_users", [])
        for user in assigned_users:
            if user.get("id") == user_id:
                return True
        
        return False
    
    def _calculate_user_burnout_metrics(
        self, 
        user_incidents: List[Dict[str, Any]], 
        analysis_days: int,
        include_weekends: bool
    ) -> Dict[str, Any]:
        """Calculate burnout metrics for a user - same methodology as Rootly."""
        # This uses the exact same calculation logic as the Rootly analyzer
        # Copy the implementation from burnout_analyzer.py for consistency
        
        total_incidents = len(user_incidents)
        
        # Calculate time-based metrics
        after_hours_count = 0
        weekend_count = 0
        total_response_time_minutes = 0
        resolved_incidents = 0
        
        for incident in user_incidents:
            created_at = incident.get("created_at")
            if created_at:
                # Check if after hours (6 PM - 8 AM)
                hour = created_at.hour
                if hour < 8 or hour >= 18:
                    after_hours_count += 1
                
                # Check if weekend (Saturday = 5, Sunday = 6)
                if created_at.weekday() >= 5:
                    weekend_count += 1
            
            # Calculate response time
            resolution_time = incident.get("resolution_time_minutes")
            if resolution_time:
                total_response_time_minutes += resolution_time
                resolved_incidents += 1
        
        # Calculate averages
        avg_response_time_minutes = (
            total_response_time_minutes / resolved_incidents 
            if resolved_incidents > 0 else 0
        )
        
        after_hours_percentage = (after_hours_count / total_incidents * 100) if total_incidents > 0 else 0
        weekend_percentage = (weekend_count / total_incidents * 100) if total_incidents > 0 else 0
        
        return {
            "total_incidents": total_incidents,
            "avg_response_time_minutes": avg_response_time_minutes,
            "after_hours_count": after_hours_count,
            "after_hours_percentage": after_hours_percentage,
            "weekend_count": weekend_count,
            "weekend_percentage": weekend_percentage,
            "resolved_incidents": resolved_incidents
        }
    
    def _calculate_burnout_factors(
        self, 
        metrics: Dict[str, Any], 
        user_incidents: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate normalized burnout factors (0-1 scale) - same methodology as Rootly."""
        # Use the exact same factor calculation as Rootly for consistency
        
        total_incidents = metrics["total_incidents"]
        
        # Workload factor (based on incident count) - more sensitive scaling
        # Scale: 0-15 incidents = 0-1.0 (was 0-20, now more sensitive)
        workload = min(total_incidents / 15.0, 1.0)
        
        # After hours factor
        after_hours = min(metrics["after_hours_percentage"] / 50.0, 1.0)  # 50% = max
        
        # Weekend work factor
        weekend_work = min(metrics["weekend_percentage"] / 30.0, 1.0)  # 30% = max
        
        # Incident load factor (frequency)
        # Assume 30-day analysis period
        incidents_per_week = (total_incidents / 30.0) * 7
        incident_load = min(incidents_per_week / 10.0, 1.0)  # 10 per week = max
        
        # Response time factor (inverse - longer response time = higher burnout)
        avg_response_hours = metrics["avg_response_time_minutes"] / 60.0
        if avg_response_hours > 0:
            # Scale: 0-8 hours = 0-1.0 (inversely)
            response_time = min(avg_response_hours / 8.0, 1.0)
        else:
            response_time = 0.0
        
        return {
            "workload": workload,
            "after_hours": after_hours,
            "weekend_work": weekend_work,
            "incident_load": incident_load,
            "response_time": response_time
        }
    
    def _calculate_overall_burnout_score(self, factors: Dict[str, float]) -> float:
        """Calculate overall burnout score using Maslach methodology - same as Rootly."""
        # Use the exact same weighted calculation as Rootly
        weights = {
            "workload": 0.25,
            "after_hours": 0.20,
            "weekend_work": 0.15,
            "incident_load": 0.25,
            "response_time": 0.15
        }
        
        weighted_score = sum(
            factors.get(factor, 0) * weight 
            for factor, weight in weights.items()
        )
        
        return min(weighted_score * 10, 10.0)  # Convert to 0-10 scale like Rootly
    
    def _determine_risk_level(self, burnout_score: float) -> str:
        """Determine risk level based on burnout score - same thresholds as Rootly (0-10 scale)."""
        if burnout_score >= 5.0:  # Same as Rootly
            return "high"
        elif burnout_score >= 3.5:  # Same as Rootly
            return "medium"
        else:
            return "low"
    
    def _calculate_team_health(self, members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall team health metrics - same methodology as Rootly."""
        if not members:
            return {
                "overall_score": 10,  # Perfect health if no data
                "risk_distribution": {"low": 0, "medium": 0, "high": 0},
                "average_burnout_score": 0,
                "health_status": "excellent",
                "members_at_risk": 0
            }
        
        # Calculate averages and distributions with null safety
        burnout_scores = [m.get("burnout_score", 0) for m in members if m and isinstance(m, dict)]
        avg_burnout = sum(burnout_scores) / len(burnout_scores) if burnout_scores else 0
        
        # Count risk levels (updated for 3-tier system)
        risk_dist = {"low": 0, "medium": 0, "high": 0}
        for member in members:
            if member and isinstance(member, dict):
                risk_level = member.get("risk_level", "low")
                if risk_level in risk_dist:
                    risk_dist[risk_level] += 1
                else:
                    risk_dist["low"] += 1
        
        # Calculate overall health score (inverse of burnout)
        # Use a more balanced approach that ensures reasonable health scores
        # even for high burnout levels
        
        # Define key thresholds and their corresponding health scores
        # This creates a piecewise linear function with gentler slopes
        if avg_burnout <= 2:
            # Low burnout (0-2) maps to excellent health (10-8.5)
            # Slope: -0.75
            overall_score = 10 - (avg_burnout * 0.75)
        elif avg_burnout <= 4:
            # Low-medium burnout (2-4) maps to good health (8.5-7)
            # Slope: -0.75
            overall_score = 8.5 - ((avg_burnout - 2) * 0.75)
        elif avg_burnout <= 6:
            # Medium burnout (4-6) maps to fair health (7-5)
            # Slope: -1.0
            overall_score = 7 - ((avg_burnout - 4) * 1.0)
        elif avg_burnout <= 8:
            # High burnout (6-8) maps to concerning health (5-3)
            # Slope: -1.0
            overall_score = 5 - ((avg_burnout - 6) * 1.0)
        else:
            # Very high burnout (8-10) maps to poor health (3-2)
            # Slope: -0.5 (gentler slope to avoid extremely low scores)
            overall_score = 3 - ((avg_burnout - 8) * 0.5)
        
        # Ensure minimum score of 2.0 (20% when displayed)
        overall_score = max(2.0, overall_score)
        
        # Determine health status
        if overall_score >= 8:
            health_status = "excellent"
        elif overall_score >= 6:
            health_status = "good"
        elif overall_score >= 4:
            health_status = "fair"
        elif overall_score >= 2:
            health_status = "poor"
        else:
            health_status = "critical"
        
        return {
            "overall_score": round(overall_score, 2),
            "risk_distribution": risk_dist,
            "average_burnout_score": round(avg_burnout, 2),
            "health_status": health_status,
            "members_at_risk": risk_dist["high"]
        }
    
    def _generate_insights(
        self, 
        team_analysis: Dict[str, Any], 
        team_health: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate insights based on team analysis - same format as Rootly."""
        insights = []
        
        risk_distribution = team_health["risk_distribution"]
        members = team_analysis.get("members", [])
        total_members = len(members)
        
        # High-risk members insight
        if risk_distribution["high"] > 0:
            insights.append({
                "type": "warning",
                "title": "High Burnout Risk Detected",
                "description": f"{risk_distribution['high']} out of {total_members} team members show high burnout risk.",
                "recommendation": "Consider redistributing workload and providing additional support."
            })
        
        # After-hours work insight
        after_hours_members = sum(
            1 for member in team_analysis["members"]
            if member.get("factors", {}).get("after_hours", 0) > 0.5
        )
        
        if after_hours_members > 0:
            insights.append({
                "type": "info",
                "title": "After-Hours Work Pattern",
                "description": f"{after_hours_members} members frequently handle incidents outside business hours.",
                "recommendation": "Review on-call rotation and incident escalation procedures."
            })
        
        return insights
    
    def _generate_recommendations(
        self, 
        team_health: Dict[str, Any], 
        team_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on Christina Maslach methodology - same format as Rootly."""
        recommendations = []
        
        risk_distribution = team_health["risk_distribution"]
        members = team_analysis.get("members", [])
        
        if risk_distribution["high"] > 0:
            recommendations.append({
                "type": "organizational",
                "priority": "high",
                "message": "Implement workload balancing for high-risk team members"
            })
            recommendations.append({
                "type": "interpersonal",
                "priority": "high", 
                "message": "Consider additional staffing or temporary support"
            })
        
        if risk_distribution["medium"] > risk_distribution["low"]:
            recommendations.append({
                "type": "personal_accomplishment",
                "priority": "medium",
                "message": "Review incident response procedures for efficiency"
            })
            recommendations.append({
                "type": "emotional_exhaustion",
                "priority": "medium",
                "message": "Provide stress management and wellness resources"
            })
        
        # Always include baseline recommendations
        recommendations.append({
            "type": "organizational",
            "priority": "low",
            "message": "Maintain regular team health check-ins"
        })
        recommendations.append({
            "type": "personal_accomplishment", 
            "priority": "low",
            "message": "Monitor incident trends and response times"
        })
        
        return recommendations