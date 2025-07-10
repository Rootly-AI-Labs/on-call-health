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
        include_weekends: bool = True,
        include_github: bool = False,
        include_slack: bool = False,
        github_token: str = None,
        slack_token: str = None
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
            
            # Create data sources structure
            data_sources = {
                "incident_data": True,
                "github_data": include_github,
                "slack_data": include_slack
            }
            
            # Collect GitHub data if enabled
            github_data = {}
            github_insights = None
            if include_github and github_token:
                try:
                    logger.info("Collecting GitHub data for team members")
                    from .github_collector import collect_team_github_data
                    
                    # Get team member emails from users data
                    team_emails = [user.get('email') for user in users if user.get('email')]
                    logger.info(f"Found {len(team_emails)} team emails for GitHub analysis")
                    
                    # Collect GitHub data
                    github_data = await collect_team_github_data(team_emails, time_range_days, github_token)
                    logger.info(f"Collected GitHub data for {len(github_data)} users")
                    
                    # Generate GitHub insights from collected data
                    github_insights = self._calculate_github_insights(github_data)
                    
                except Exception as e:
                    logger.error(f"Error collecting GitHub data: {e}")
                    github_insights = {
                        "total_users_analyzed": 0,
                        "avg_commits_per_week": 0,
                        "avg_prs_per_week": 0,
                        "after_hours_activity_rate": 0,
                        "weekend_activity_rate": 0,
                        "top_contributors": [],
                        "burnout_indicators": {
                            "excessive_commits": 0,
                            "after_hours_coding": 0,
                            "weekend_work": 0,
                            "large_prs": 0
                        }
                    }
            elif include_github:
                logger.warning("GitHub integration enabled but no token provided")
                github_insights = {
                    "total_users_analyzed": 0,
                    "avg_commits_per_week": 0,
                    "avg_prs_per_week": 0,
                    "after_hours_activity_rate": 0,
                    "weekend_activity_rate": 0,
                    "top_contributors": [],
                    "burnout_indicators": {
                        "excessive_commits": 0,
                        "after_hours_coding": 0,
                        "weekend_work": 0,
                        "large_prs": 0
                    }
                }
            
            # Collect Slack data if enabled
            slack_data = {}
            slack_insights = None
            if include_slack and slack_token:
                try:
                    logger.info("Collecting Slack data for team members")
                    from .slack_collector import collect_team_slack_data
                    
                    # Get team member names from users data
                    team_names = [user.get('name') for user in users if user.get('name')]
                    logger.info(f"Found {len(team_names)} team names for Slack analysis")
                    
                    # Collect Slack data using names
                    slack_data = await collect_team_slack_data(team_names, time_range_days, slack_token, use_names=True)
                    logger.info(f"Collected Slack data for {len(slack_data)} users")
                    
                    # Generate Slack insights from collected data
                    slack_insights = self._calculate_slack_insights(slack_data)
                    
                except Exception as e:
                    logger.error(f"Error collecting Slack data: {e}")
                    slack_insights = {
                        "total_users_analyzed": 0,
                        "avg_messages_per_day": 0,
                        "avg_response_time_minutes": 0,
                        "after_hours_messaging_rate": 0,
                        "weekend_messaging_rate": 0,
                        "avg_sentiment_score": 0,
                        "channels_analyzed": 0,
                        "burnout_indicators": {
                            "excessive_messaging": 0,
                            "poor_sentiment": 0,
                            "late_responses": 0,
                            "after_hours_activity": 0
                        }
                    }
            elif include_slack:
                logger.warning("Slack integration enabled but no token provided")
                slack_insights = {
                    "total_users_analyzed": 0,
                    "avg_messages_per_day": 0,
                    "avg_response_time_minutes": 0,
                    "after_hours_messaging_rate": 0,
                    "weekend_messaging_rate": 0,
                    "avg_sentiment_score": 0,
                    "channels_analyzed": 0,
                    "burnout_indicators": {
                        "excessive_messaging": 0,
                        "poor_sentiment": 0,
                        "late_responses": 0,
                        "after_hours_activity": 0
                    }
                }

            result = {
                "analysis_timestamp": datetime.now().isoformat(),
                "metadata": {
                    **metadata,
                    "include_weekends": include_weekends,
                    "include_github": include_github,
                    "include_slack": include_slack
                },
                "data_sources": data_sources,
                "team_health": team_health,
                "team_analysis": team_analysis,
                "insights": insights,
                "recommendations": self._generate_recommendations(team_health, team_analysis)
            }
            
            # Add GitHub insights if enabled
            if github_insights:
                result["github_insights"] = github_insights
                
            # Add Slack insights if enabled  
            if slack_insights:
                result["slack_insights"] = slack_insights
                
            return result
            
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
    
    def _calculate_github_insights(self, github_data: Dict[str, Dict]) -> Dict[str, Any]:
        """Calculate aggregated GitHub insights from team data."""
        if not github_data:
            return {
                "total_users_analyzed": 0,
                "avg_commits_per_week": 0,
                "avg_prs_per_week": 0,
                "after_hours_activity_rate": 0,
                "weekend_activity_rate": 0,
                "top_contributors": [],
                "burnout_indicators": {
                    "excessive_commits": 0,
                    "after_hours_coding": 0,
                    "weekend_work": 0,
                    "large_prs": 0
                }
            }
        
        users_with_data = len(github_data)
        all_metrics = [data.get("metrics", {}) for data in github_data.values()]
        
        # Calculate averages
        total_commits_per_week = sum(m.get("commits_per_week", 0) for m in all_metrics)
        total_prs_per_week = sum(m.get("prs_per_week", 0) for m in all_metrics)
        
        avg_commits_per_week = total_commits_per_week / users_with_data if users_with_data > 0 else 0
        avg_prs_per_week = total_prs_per_week / users_with_data if users_with_data > 0 else 0
        
        # Calculate after-hours and weekend rates
        after_hours_rates = [m.get("after_hours_commit_percentage", 0) for m in all_metrics]
        weekend_rates = [m.get("weekend_commit_percentage", 0) for m in all_metrics]
        
        avg_after_hours_rate = sum(after_hours_rates) / len(after_hours_rates) if after_hours_rates else 0
        avg_weekend_rate = sum(weekend_rates) / len(weekend_rates) if weekend_rates else 0
        
        # Count burnout indicators
        burnout_counts = {
            "excessive_commits": 0,
            "after_hours_coding": 0,
            "weekend_work": 0,
            "large_prs": 0
        }
        
        for data in github_data.values():
            indicators = data.get("burnout_indicators", {})
            for key in burnout_counts:
                if indicators.get(key, False):
                    burnout_counts[key] += 1
        
        # Top contributors (top 5 by commits)
        contributors = []
        for email, data in github_data.items():
            metrics = data.get("metrics", {})
            contributors.append({
                "email": email,
                "username": data.get("username", ""),
                "commits_per_week": metrics.get("commits_per_week", 0),
                "total_commits": metrics.get("total_commits", 0)
            })
        
        top_contributors = sorted(contributors, key=lambda x: x["total_commits"], reverse=True)[:5]
        
        # Calculate totals for the team
        total_commits = sum(m.get("total_commits", 0) for m in all_metrics)
        total_prs = sum(m.get("total_pull_requests", 0) for m in all_metrics)
        total_reviews = sum(m.get("total_reviews", 0) for m in all_metrics)
        
        return {
            "total_users_analyzed": users_with_data,
            "total_commits": total_commits,
            "total_pull_requests": total_prs,
            "total_reviews": total_reviews,
            "avg_commits_per_week": round(avg_commits_per_week, 2),
            "avg_prs_per_week": round(avg_prs_per_week, 2),
            "after_hours_activity_rate": round(avg_after_hours_rate, 3),
            "after_hours_activity_percentage": round(avg_after_hours_rate * 100, 1),  # Frontend expects percentage
            "weekend_activity_rate": round(avg_weekend_rate, 3),
            "top_contributors": top_contributors,
            "burnout_indicators": {
                "excessive_commits": burnout_counts.get("excessive_commits", 0),
                "after_hours_coding": burnout_counts.get("after_hours_coding", 0),
                "weekend_work": burnout_counts.get("weekend_work", 0),
                "large_prs": burnout_counts.get("large_prs", 0),
                # Frontend specific field names
                "excessive_late_night_commits": burnout_counts.get("after_hours_coding", 0),
                "weekend_workers": burnout_counts.get("weekend_work", 0),
                "large_pr_pattern": burnout_counts.get("large_prs", 0)
            }
        }
    
    def _calculate_slack_insights(self, slack_data: Dict[str, Dict]) -> Dict[str, Any]:
        """Calculate aggregated Slack insights from team data."""
        if not slack_data:
            return {
                "total_users_analyzed": 0,
                "avg_messages_per_day": 0,
                "avg_response_time_minutes": 0,
                "after_hours_messaging_rate": 0,
                "weekend_messaging_rate": 0,
                "avg_sentiment_score": 0,
                "channels_analyzed": 0,
                "burnout_indicators": {
                    "excessive_messaging": 0,
                    "poor_sentiment": 0,
                    "late_responses": 0,
                    "after_hours_activity": 0
                },
                "errors": {
                    "rate_limited_channels": [],
                    "other_errors": []
                }
            }
        
        # Check for rate limiting errors in the data
        rate_limited_channels = set()
        other_errors = []
        
        for user_data in slack_data.values():
            fetch_errors = user_data.get("fetch_errors", {})
            rate_limited_channels.update(fetch_errors.get("rate_limited_channels", []))
            other_errors.extend(fetch_errors.get("errors", []))
        
        users_with_data = len(slack_data)
        all_metrics = [data.get("metrics", {}) for data in slack_data.values()]
        
        # Calculate averages
        total_messages_per_day = sum(m.get("messages_per_day", 0) for m in all_metrics)
        total_response_times = [m.get("avg_response_time_minutes", 0) for m in all_metrics if m.get("avg_response_time_minutes", 0) > 0]
        
        avg_messages_per_day = total_messages_per_day / users_with_data if users_with_data > 0 else 0
        avg_response_time = sum(total_response_times) / len(total_response_times) if total_response_times else 0
        
        # Calculate after-hours and weekend rates
        after_hours_rates = [m.get("after_hours_percentage", 0) for m in all_metrics]
        weekend_rates = [m.get("weekend_percentage", 0) for m in all_metrics]
        sentiment_scores = [m.get("avg_sentiment", 0) for m in all_metrics]
        
        avg_after_hours_rate = sum(after_hours_rates) / len(after_hours_rates) if after_hours_rates else 0
        avg_weekend_rate = sum(weekend_rates) / len(weekend_rates) if weekend_rates else 0
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # Count unique channels
        all_channels = set()
        for data in slack_data.values():
            metrics = data.get("metrics", {})
            channel_count = metrics.get("channel_diversity", 0)
            # This is an approximation since we don't have actual channel IDs
            all_channels.add(f"user_{data.get('user_id', '')}_channels_{channel_count}")
        
        # Count burnout indicators
        burnout_counts = {
            "excessive_messaging": 0,
            "poor_sentiment": 0,
            "late_responses": 0,
            "after_hours_activity": 0
        }
        
        for data in slack_data.values():
            indicators = data.get("burnout_indicators", {})
            for key in burnout_counts:
                if indicators.get(key, False):
                    burnout_counts[key] += 1
        
        # Calculate totals for the team
        total_messages = sum(m.get("total_messages", 0) for m in all_metrics)
        total_channels = sum(m.get("channel_diversity", 0) for m in all_metrics)
        
        return {
            "total_users_analyzed": users_with_data,
            "total_messages": total_messages,
            "active_channels": total_channels,
            "avg_messages_per_day": round(avg_messages_per_day, 1),
            "avg_response_time_minutes": round(avg_response_time, 1),
            "after_hours_messaging_rate": round(avg_after_hours_rate, 3),
            "after_hours_activity_percentage": round(avg_after_hours_rate * 100, 1),  # Frontend expects percentage
            "weekend_messaging_rate": round(avg_weekend_rate, 3),
            "avg_sentiment_score": round(avg_sentiment, 3),
            "channels_analyzed": len(all_channels),
            "sentiment_analysis": {
                "overall_sentiment": "positive" if avg_sentiment > 0.1 else "neutral" if avg_sentiment > -0.1 else "negative",
                "sentiment_score": round(avg_sentiment, 3),
                "positive_ratio": round(sum(m.get("positive_sentiment_ratio", 0) for m in all_metrics) / users_with_data, 3) if users_with_data > 0 else 0,
                "negative_ratio": round(sum(m.get("negative_sentiment_ratio", 0) for m in all_metrics) / users_with_data, 3) if users_with_data > 0 else 0
            },
            "burnout_indicators": {
                "excessive_messaging": burnout_counts.get("excessive_messaging", 0),
                "poor_sentiment": burnout_counts.get("poor_sentiment", 0),
                "late_responses": burnout_counts.get("late_responses", 0),
                "after_hours_activity": burnout_counts.get("after_hours_activity", 0)
            },
            "errors": {
                "rate_limited_channels": list(rate_limited_channels),
                "other_errors": other_errors
            }
        }