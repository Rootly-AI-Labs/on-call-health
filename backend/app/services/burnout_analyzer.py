"""
Burnout analysis service for analyzing incident patterns and calculating burnout metrics.
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

from ..core.rootly_client import RootlyAPIClient
from .ai_burnout_analyzer import get_ai_burnout_analyzer

logger = logging.getLogger(__name__)


class BurnoutAnalyzerService:
    """Service for analyzing burnout based on Rootly incident data."""
    
    def __init__(self, api_token: str):
        self.client = RootlyAPIClient(api_token)
        
        # Burnout scoring thresholds
        self.thresholds = {
            "incidents_per_week": {
                "low": 3,
                "medium": 6,
                "high": 10
            },
            "after_hours_percentage": {
                "low": 0.1,    # 10%
                "medium": 0.25, # 25%
                "high": 0.4     # 40%
            },
            "weekend_percentage": {
                "low": 0.05,    # 5%
                "medium": 0.15, # 15%
                "high": 0.25    # 25%
            },
            "avg_response_time_minutes": {
                "low": 15,
                "medium": 30,
                "high": 60
            },
            "severity_weight": {
                "critical": 3.0,
                "high": 2.0,
                "medium": 1.5,
                "low": 1.0
            }
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
        
        Returns structured analysis results with:
        - Overall team health score
        - Individual member burnout scores
        - Burnout factors
        """
        logger.info(f"Starting burnout analysis for {time_range_days} days")
        
        try:
            # Fetch data from Rootly
            logger.info(f"TRACE: About to call _fetch_analysis_data for {time_range_days} days")
            data = await self._fetch_analysis_data(time_range_days)
            logger.info(f"TRACE: _fetch_analysis_data returned: type={type(data)}, is_none={data is None}")
            
            # Check if data was successfully fetched (data should never be None due to fallbacks)
            if data is None:
                logger.error("TRACE: Data is None after _fetch_analysis_data")
                raise Exception("Failed to fetch data from Rootly API - no data returned")
            
            # Extract users and incidents (with additional safety checks)
            logger.info(f"TRACE: About to extract users and incidents from data")
            users = data.get("users", []) if data else []
            incidents = data.get("incidents", []) if data else []
            metadata = data.get("collection_metadata", {}) if data else {}
            logger.info(f"TRACE: Extracted {len(users)} users, {len(incidents)} incidents")
            
            # Collect GitHub/Slack data if enabled
            github_data = {}
            slack_data = {}
            
            if include_github or include_slack:
                from .github_collector import collect_team_github_data
                from .slack_collector import collect_team_slack_data
                
                # Get team member emails and names from JSONAPI format
                team_emails = []
                team_names = []
                for user in users:
                    if isinstance(user, dict) and "attributes" in user:
                        attrs = user["attributes"]
                        email = attrs.get("email")
                        name = attrs.get("full_name") or attrs.get("name")
                        if email:
                            team_emails.append(email)
                        if name:
                            team_names.append(name)
                    elif isinstance(user, dict):
                        # Fallback for non-JSONAPI format
                        email = user.get("email")
                        name = user.get("full_name") or user.get("name")
                        if email:
                            team_emails.append(email)
                        if name:
                            team_names.append(name)
                
                if include_github:
                    logger.info(f"Collecting GitHub data for {len(team_emails)} team members")
                    logger.info(f"Team emails: {team_emails[:5]}...")  # Log first 5 emails
                    try:
                        logger.info(f"GitHub config - token: {'present' if github_token else 'missing'}")
                        
                        github_data = await collect_team_github_data(
                            team_emails, time_range_days, github_token
                        )
                        logger.info(f"Collected GitHub data for {len(github_data)} users")
                        logger.info(f"GitHub data keys: {list(github_data.keys())[:5]}")  # Log first 5 keys
                    except Exception as e:
                        logger.error(f"GitHub data collection failed: {e}")
                
                if include_slack:
                    logger.info(f"Collecting Slack data for {len(team_names)} team members using names")
                    logger.info(f"Team names: {team_names[:5]}...")  # Log first 5 names
                    try:
                        logger.info(f"Slack config - token: {'present' if slack_token else 'missing'}")
                        
                        # Use names for Slack correlation instead of emails
                        slack_data = await collect_team_slack_data(
                            team_names, time_range_days, slack_token, use_names=True
                        )
                        logger.info(f"Collected Slack data for {len(slack_data)} users")
                    except Exception as e:
                        logger.error(f"Slack data collection failed: {e}")
            
            # Analyze team burnout
            try:
                logger.info(f"TRACE: About to call _analyze_team_data with {len(users)} users, {len(incidents)} incidents")
                team_analysis = self._analyze_team_data(
                    users, 
                    incidents, 
                    metadata,
                    include_weekends,
                    github_data,
                    slack_data
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
            
            # Create GitHub insights if enabled
            github_insights = None
            if include_github:
                github_insights = self._calculate_github_insights(github_data)
            
            # Create Slack insights if enabled  
            slack_insights = None
            if include_slack:
                slack_insights = self._calculate_slack_insights(slack_data)

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
            
            # Enhance with AI analysis
            available_integrations = []
            if include_github:
                available_integrations.append('github')
            if include_slack:
                available_integrations.append('slack')
            
            result = await self._enhance_with_ai_analysis(result, available_integrations)
                
            return result
            
        except Exception as e:
            logger.error(f"Burnout analysis failed: {e}")
            raise
    
    async def _fetch_analysis_data(self, days_back: int) -> Dict[str, Any]:
        """Fetch all required data from Rootly API."""
        try:
            # Use the existing data collection method
            logger.info(f"Fetching analysis data for {days_back} days")
            data = await self.client.collect_analysis_data(days_back=days_back)
            
            # Add detailed logging to debug the NoneType issue
            logger.info(f"Data from collect_analysis_data: type={type(data)}, value={data}")
            
            # Ensure we always have a valid data structure
            if data is None:
                logger.warning("collect_analysis_data returned None, creating fallback data structure")
                data = {
                    "users": [],
                    "incidents": [],
                    "collection_metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "days_analyzed": days_back,
                        "total_users": 0,
                        "total_incidents": 0,
                        "error": "Data collection returned None",
                        "date_range": {
                            "start": (datetime.now() - timedelta(days=days_back)).isoformat(),
                            "end": datetime.now().isoformat()
                        }
                    }
                }
            
            # Additional safety check
            if not isinstance(data, dict):
                logger.error(f"Data is not a dictionary! Type: {type(data)}, Value: {data}")
                data = {
                    "users": [],
                    "incidents": [],
                    "collection_metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "days_analyzed": days_back,
                        "total_users": 0,
                        "total_incidents": 0,
                        "error": f"Data collection returned invalid type: {type(data)}",
                        "date_range": {
                            "start": (datetime.now() - timedelta(days=days_back)).isoformat(),
                            "end": datetime.now().isoformat()
                        }
                    }
                }
            
            # Add additional safety check for logging
            if data and isinstance(data, dict):
                logger.info(f"Successfully fetched data: {len(data.get('users', []))} users, {len(data.get('incidents', []))} incidents")
            else:
                logger.warning(f"Data is not a valid dictionary: type={type(data)}, value={data}")
            return data
        except Exception as e:
            logger.error(f"Error fetching analysis data: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Full exception details: {repr(e)}")
            # Return fallback data instead of raising
            return {
                "users": [],
                "incidents": [],
                "collection_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "days_analyzed": days_back,
                    "total_users": 0,
                    "total_incidents": 0,
                    "error": str(e),
                    "date_range": {
                        "start": (datetime.now() - timedelta(days=days_back)).isoformat(),
                        "end": datetime.now().isoformat()
                    }
                }
            }
    
    def _analyze_team_data(
        self, 
        users: List[Dict[str, Any]], 
        incidents: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        include_weekends: bool,
        github_data: Dict[str, Dict] = None,
        slack_data: Dict[str, Dict] = None
    ) -> Dict[str, Any]:
        """Analyze burnout data for the entire team."""
        # Ensure all inputs are valid
        users = users or []
        incidents = incidents or []
        metadata = metadata or {}
        
        # Map users to their incidents
        user_incidents = self._map_user_incidents(users, incidents)
        
        # Analyze each team member
        member_analyses = []
        for user in users:
            # Add safety check for None user
            if user is None:
                continue
            user_id = str(user.get("id")) if user.get("id") is not None else "unknown"
            # Get GitHub/Slack data for this user - handle JSONAPI format
            if isinstance(user, dict) and "attributes" in user:
                user_email = user["attributes"].get("email")
                user_name = user["attributes"].get("full_name") or user["attributes"].get("name")
            else:
                user_email = user.get("email")
                user_name = user.get("full_name") or user.get("name")
            
            # GitHub uses email, Slack uses name
            user_github_data = github_data.get(user_email) if github_data and user_email else None
            user_slack_data = slack_data.get(user_name) if slack_data and user_name else None
            
            user_analysis = self._analyze_member_burnout(
                user,
                user_incidents.get(user_id, []),
                metadata,
                include_weekends,
                user_github_data,
                user_slack_data
            )
            member_analyses.append(user_analysis)
        
        # Sort by burnout score (highest first)
        member_analyses.sort(key=lambda x: x["burnout_score"], reverse=True)
        
        return {
            "members": member_analyses,
            "total_members": len(users),
            "total_incidents": len(incidents)
        }
    
    def _map_user_incidents(
        self, 
        users: List[Dict[str, Any]], 
        incidents: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Map incidents to users based on involvement."""
        user_incidents = defaultdict(list)
        
        # Ensure inputs are valid
        incidents = incidents or []
        
        for incident in incidents:
            # Add safety check for None incident
            if incident is None:
                continue
            attrs = incident.get("attributes", {}) if incident else {}
            incident_users = set()
            
            # Extract all users involved in the incident with comprehensive null safety
            # Creator/Reporter
            user_data = attrs.get("user")
            if user_data and isinstance(user_data, dict):
                data = user_data.get("data")
                if data and isinstance(data, dict) and data.get("id"):
                    incident_users.add(str(data["id"]))
            
            # Started by (acknowledged)
            started_by_data = attrs.get("started_by")
            if started_by_data and isinstance(started_by_data, dict):
                data = started_by_data.get("data")
                if data and isinstance(data, dict) and data.get("id"):
                    incident_users.add(str(data["id"]))
            
            # Resolved by
            resolved_by_data = attrs.get("resolved_by")
            if resolved_by_data and isinstance(resolved_by_data, dict):
                data = resolved_by_data.get("data")
                if data and isinstance(data, dict) and data.get("id"):
                    incident_users.add(str(data["id"]))
            
            # Add incident to each involved user
            for user_id in incident_users:
                user_incidents[user_id].append(incident)
        
        return dict(user_incidents)
    
    def _analyze_member_burnout(
        self,
        user: Dict[str, Any],
        incidents: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        include_weekends: bool,
        github_data: Dict[str, Any] = None,
        slack_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Analyze burnout for a single team member."""
        user_attrs = user.get("attributes", {})
        user_id = user.get("id")
        user_name = user_attrs.get("full_name") or user_attrs.get("name", "Unknown")
        user_email = user_attrs.get("email")
        
        # If no incidents, return minimal analysis
        if not incidents:
            return {
                "user_id": user_id,
                "user_name": user_name,
                "user_email": user_email,
                "burnout_score": 0,
                "risk_level": "low",
                "incident_count": 0,
                "factors": {
                    "workload": 0,
                    "after_hours": 0,
                    "weekend_work": 0,
                    "incident_load": 0,
                    "response_time": 0
                },
                "maslach_dimensions": {
                    "emotional_exhaustion": 0,
                    "depersonalization": 0,
                    "personal_accomplishment": 10
                },
                "metrics": {
                    "incidents_per_week": 0,
                    "after_hours_percentage": 0,
                    "weekend_percentage": 0,
                    "avg_response_time_minutes": 0,
                    "severity_distribution": {}
                }
            }
        
        # Calculate metrics
        days_analyzed = metadata.get("days_analyzed", 30)
        metrics = self._calculate_member_metrics(
            incidents, 
            days_analyzed, 
            include_weekends
        )
        
        # Calculate Maslach dimensions
        dimensions = self._calculate_maslach_dimensions(metrics)
        
        # Calculate burnout factors for backward compatibility
        factors = self._calculate_burnout_factors(metrics)
        
        # Calculate overall burnout score using Maslach methodology
        # Ensure personal accomplishment is properly bounded to prevent negative scores
        pa_score = min(10, max(0, dimensions["personal_accomplishment"]))
        burnout_score = (dimensions["emotional_exhaustion"] * 0.4 + 
                        dimensions["depersonalization"] * 0.3 + 
                        (10 - pa_score) * 0.3)
        
        # Ensure overall score is never negative
        burnout_score = max(0, burnout_score)
        
        # Determine risk level
        risk_level = self._determine_risk_level(burnout_score)
        
        result = {
            "user_id": user_id,
            "user_name": user_name,
            "user_email": user_email,
            "burnout_score": round(burnout_score, 2),
            "risk_level": risk_level,
            "incident_count": len(incidents),
            "factors": factors,
            "maslach_dimensions": dimensions,
            "metrics": metrics
        }
        
        # Add GitHub activity if available
        if github_data and github_data.get("activity_data"):
            result["github_activity"] = github_data["activity_data"]
        else:
            # Add placeholder GitHub activity
            result["github_activity"] = {
                "commits_count": 0,
                "pull_requests_count": 0,
                "reviews_count": 0,
                "after_hours_commits": 0,
                "weekend_commits": 0,
                "avg_pr_size": 0,
                "burnout_indicators": {
                    "excessive_commits": False,
                    "late_night_activity": False,
                    "weekend_work": False,
                    "large_prs": False
                }
            }
        
        # Add Slack activity if available
        if slack_data and slack_data.get("activity_data"):
            result["slack_activity"] = slack_data["activity_data"]
        else:
            # Add placeholder Slack activity
            result["slack_activity"] = {
                "messages_sent": 0,
                "channels_active": 0,
                "after_hours_messages": 0,
                "weekend_messages": 0,
                "avg_response_time_minutes": 0,
                "sentiment_score": 0.0,
                "burnout_indicators": {
                    "excessive_messaging": False,
                    "poor_sentiment": False,
                    "late_responses": False,
                    "after_hours_activity": False
                }
            }
        
        return result
    
    def _calculate_member_metrics(
        self,
        incidents: List[Dict[str, Any]],
        days_analyzed: int,
        include_weekends: bool
    ) -> Dict[str, Any]:
        """Calculate detailed metrics for a team member."""
        # Initialize counters
        after_hours_count = 0
        weekend_count = 0
        response_times = []
        severity_counts = defaultdict(int)
        
        for incident in incidents:
            attrs = incident.get("attributes", {})
            
            # Check timing
            created_at = attrs.get("created_at")
            if created_at:
                dt = self._parse_timestamp(created_at)
                if dt:
                    # After hours: before 9 AM or after 6 PM
                    if dt.hour < 9 or dt.hour >= 18:
                        after_hours_count += 1
                    
                    # Weekend: Saturday (5) or Sunday (6)
                    if dt.weekday() >= 5:
                        weekend_count += 1
            
            # Response time (time to acknowledge)
            started_at = attrs.get("started_at")
            if created_at and started_at:
                response_time = self._calculate_response_time(created_at, started_at)
                if response_time is not None:
                    response_times.append(response_time)
            
            # Severity with null safety
            severity = "unknown"
            severity_data = attrs.get("severity")
            if severity_data and isinstance(severity_data, dict):
                data = severity_data.get("data")
                if data and isinstance(data, dict):
                    attributes = data.get("attributes")
                    if attributes and isinstance(attributes, dict):
                        name = attributes.get("name")
                        if name and isinstance(name, str):
                            severity = name.lower()
            severity_counts[severity] += 1
        
        # Calculate averages and percentages
        incidents_per_week = (len(incidents) / days_analyzed) * 7
        after_hours_percentage = after_hours_count / len(incidents) if incidents else 0
        weekend_percentage = weekend_count / len(incidents) if incidents else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "incidents_per_week": round(incidents_per_week, 2),
            "after_hours_percentage": round(after_hours_percentage, 3),
            "weekend_percentage": round(weekend_percentage, 3),
            "avg_response_time_minutes": round(avg_response_time, 1),
            "severity_distribution": dict(severity_counts)
        }
    
    def _calculate_maslach_dimensions(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """Calculate Maslach Burnout Inventory dimensions (0-10 scale each)."""
        # Currently only implementing incident-based calculations (70% weight)
        # GitHub (15%) and Slack (15%) components to be added later
        
        # Emotional Exhaustion (40% of final score)
        emotional_exhaustion = self._calculate_emotional_exhaustion_incident(metrics)
        
        # Depersonalization (30% of final score)
        depersonalization = self._calculate_depersonalization_incident(metrics)
        
        # Personal Accomplishment (30% of final score, inverted)
        personal_accomplishment = self._calculate_personal_accomplishment_incident(metrics)
        
        return {
            "emotional_exhaustion": round(emotional_exhaustion, 2),
            "depersonalization": round(depersonalization, 2),
            "personal_accomplishment": round(personal_accomplishment, 2)
        }
    
    def _calculate_emotional_exhaustion_incident(self, metrics: Dict[str, Any]) -> float:
        """Calculate Emotional Exhaustion from incident data (0-10 scale)."""
        # Incident frequency score - more realistic thresholds
        ipw = metrics["incidents_per_week"]
        # Scale: 0-2 incidents/week = 0-3, 2-5 = 3-7, 5-8 = 7-10, 8+ = 10
        if ipw <= 2:
            incident_frequency_score = ipw * 1.5  # 0-3 range
        elif ipw <= 5:
            incident_frequency_score = 3 + ((ipw - 2) / 3) * 4  # 3-7 range
        elif ipw <= 8:
            incident_frequency_score = 7 + ((ipw - 5) / 3) * 3  # 7-10 range
        else:
            incident_frequency_score = 10  # 8+ incidents per week = maximum burnout
        
        # After hours score
        ahp = metrics["after_hours_percentage"]
        after_hours_score = min(10, ahp * 20)
        
        # Resolution time score (using response time as proxy)
        art = metrics["avg_response_time_minutes"]
        resolution_time_score = min(10, (art / 60) * 10)  # Normalize to hours
        
        # Clustering score (simplified - assume 20% clustering for now)
        clustering_score = min(10, 0.2 * 15)  # Placeholder
        
        # Weighted average with incident frequency as primary factor (50% weight)
        return (incident_frequency_score * 0.5 + after_hours_score * 0.2 + resolution_time_score * 0.2 + clustering_score * 0.1)
    
    def _calculate_depersonalization_incident(self, metrics: Dict[str, Any]) -> float:
        """Calculate Depersonalization from incident data (0-10 scale)."""
        # Escalation score (using severity as proxy)
        severity_dist = metrics["severity_distribution"]
        high_severity_count = severity_dist.get("high", 0) + severity_dist.get("critical", 0)
        total_incidents = sum(severity_dist.values()) if severity_dist else 1
        escalation_rate = high_severity_count / total_incidents if total_incidents > 0 else 0
        escalation_score = min(10, escalation_rate * 10)
        
        # Solo work score (assume 30% solo work for now)
        solo_work_score = min(10, 0.3 * 10)  # Placeholder
        
        # Response trend score (assume stable for now)
        response_trend_score = 0  # Placeholder
        
        # Communication score (assume average communication for now)
        communication_score = 5  # Placeholder
        
        # Mean of all components
        return (escalation_score + solo_work_score + response_trend_score + communication_score) / 4
    
    def _calculate_personal_accomplishment_incident(self, metrics: Dict[str, Any]) -> float:
        """Calculate Personal Accomplishment from incident data (0-10 scale)."""
        # Resolution success score (assume 80% success rate for now)
        resolution_success_score = 8.0  # Placeholder
        
        # Improvement score (assume stable performance for now)
        improvement_score = 5.0  # Placeholder
        
        # Complexity score (using severity distribution)
        severity_dist = metrics["severity_distribution"]
        high_severity_count = severity_dist.get("high", 0) + severity_dist.get("critical", 0)
        total_incidents = sum(severity_dist.values()) if severity_dist else 1
        high_severity_rate = high_severity_count / total_incidents if total_incidents > 0 else 0
        complexity_score = high_severity_rate * 10
        
        # Knowledge sharing score (assume minimal for now)
        knowledge_sharing_score = 2.0  # Placeholder
        
        # Mean of all components
        return (resolution_success_score + improvement_score + complexity_score + knowledge_sharing_score) / 4
    
    def _calculate_burnout_factors(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """Calculate individual burnout factors for UI display."""
        # Calculate factors that properly reflect incident load
        incidents_per_week = metrics.get("incidents_per_week", 0)
        
        # Workload factor based on incident frequency (more direct)
        # Scale: 0-2 incidents/week = 0-3, 2-5 = 3-7, 5-8 = 7-10, 8+ = 10
        if incidents_per_week <= 2:
            workload = incidents_per_week * 1.5
        elif incidents_per_week <= 5:
            workload = 3 + ((incidents_per_week - 2) / 3) * 4
        elif incidents_per_week <= 8:
            workload = 7 + ((incidents_per_week - 5) / 3) * 3
        else:
            workload = 10
        
        # After hours factor 
        after_hours = min(10, metrics["after_hours_percentage"] * 20)
        
        # Weekend work factor
        weekend_work = min(10, metrics["weekend_percentage"] * 25)
        
        # Incident load factor (direct calculation based on weekly incident rate)
        # Scale: 0-3 incidents/week = 0-3, 3-6 = 3-7, 6-10 = 7-10, 10+ = 10
        if incidents_per_week <= 3:
            incident_load = incidents_per_week
        elif incidents_per_week <= 6:
            incident_load = 3 + ((incidents_per_week - 3) / 3) * 4
        elif incidents_per_week <= 10:
            incident_load = 7 + ((incidents_per_week - 6) / 4) * 3
        else:
            incident_load = 10
        
        # Response time factor
        response_time = min(10, metrics["avg_response_time_minutes"] / 6)
        
        factors = {
            "workload": workload,
            "after_hours": after_hours, 
            "weekend_work": weekend_work,
            "incident_load": incident_load,
            "response_time": response_time
        }
        
        return {k: round(v, 2) for k, v in factors.items()}
    
    def _calculate_burnout_score(self, factors: Dict[str, float]) -> float:
        """Calculate overall burnout score using Maslach methodology."""
        # First get the metrics to calculate proper dimensions
        # For now, we'll use the factors to approximate dimensions
        
        # Approximate Emotional Exhaustion from factors
        emotional_exhaustion = (factors.get("workload", 0) * 0.4 + 
                              factors.get("after_hours", 0) * 0.3 + 
                              factors.get("incident_load", 0) * 0.3)
        
        # Approximate Depersonalization from factors
        depersonalization = (factors.get("response_time", 0) * 0.5 + 
                           factors.get("workload", 0) * 0.3 + 
                           factors.get("weekend_work", 0) * 0.2)
        
        # Approximate Personal Accomplishment (inverted)
        personal_accomplishment = 10 - (factors.get("response_time", 0) * 0.3 + 
                                       factors.get("workload", 0) * 0.4 + 
                                       factors.get("incident_load", 0) * 0.3)
        personal_accomplishment = max(0, personal_accomplishment)
        
        # Calculate final score using Maslach weights
        # Ensure personal accomplishment is properly bounded to prevent negative scores
        pa_score = min(10, max(0, personal_accomplishment))
        burnout_score = (emotional_exhaustion * 0.4 + 
                        depersonalization * 0.3 + 
                        (10 - pa_score) * 0.3)
        
        # Ensure overall score is never negative
        return max(0, burnout_score)
    
    def _determine_risk_level(self, burnout_score: float) -> str:
        """Determine risk level based on burnout score using Maslach methodology."""
        if burnout_score >= 5.0:  # Further lowered to catch high-incident users
            return "high"
        elif burnout_score >= 3.5:  # Lowered from 4.0 to catch moderate cases
            return "medium"
        else:
            return "low"
    
    def _calculate_team_health(self, member_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall team health metrics."""
        if not member_analyses:
            return {
                "overall_score": 10,  # Perfect health if no data
                "risk_distribution": {"low": 0, "medium": 0, "high": 0},
                "average_burnout_score": 0,
                "health_status": "excellent",
                "members_at_risk": 0
            }
        
        # Calculate averages and distributions with null safety
        burnout_scores = [m.get("burnout_score", 0) for m in member_analyses if m and isinstance(m, dict)]
        avg_burnout = sum(burnout_scores) / len(burnout_scores) if burnout_scores else 0
        
        # Count risk levels (updated for 3-tier system)
        risk_dist = {"low": 0, "medium": 0, "high": 0}
        for member in member_analyses:
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
        """Generate insights from the analysis."""
        insights = []
        members = team_analysis.get("members", []) if team_analysis else []
        
        # Team-level insights with null safety
        members_at_risk = team_health.get("members_at_risk", 0) if team_health else 0
        if members_at_risk > 0:
            insights.append({
                "type": "warning",
                "category": "team",
                "message": f"{members_at_risk} team members are at high burnout risk",
                "priority": "high"
            })
        
        # Find common patterns
        if members:
            # High after-hours work
            high_after_hours = [m for m in members if m["metrics"]["after_hours_percentage"] > 0.3]
            if len(high_after_hours) >= len(members) * 0.3:
                insights.append({
                    "type": "pattern",
                    "category": "after_hours",
                    "message": f"{len(high_after_hours)} team members have >30% after-hours incidents",
                    "priority": "high"
                })
            
            # Weekend work patterns
            high_weekend = [m for m in members if m["metrics"]["weekend_percentage"] > 0.2]
            if len(high_weekend) >= len(members) * 0.25:
                insights.append({
                    "type": "pattern",
                    "category": "weekend_work",
                    "message": f"{len(high_weekend)} team members regularly handle weekend incidents",
                    "priority": "medium"
                })
            
            # Response time issues
            slow_response = [m for m in members if m["metrics"]["avg_response_time_minutes"] > 45]
            if slow_response:
                insights.append({
                    "type": "metric",
                    "category": "response_time",
                    "message": f"{len(slow_response)} team members have average response times >45 minutes",
                    "priority": "medium"
                })
        
        return insights
    
    def _generate_recommendations(
        self, 
        team_health: Dict[str, Any], 
        team_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on Christina Maslach methodology."""
        recommendations = []
        members = team_analysis.get("members", []) if team_analysis else []
        
        # Team health recommendations with null safety
        health_status = team_health.get("health_status", "unknown") if team_health else "unknown"
        members_at_risk = team_health.get("members_at_risk", 0) if team_health else 0
        
        if health_status in ["poor", "fair"]:
            recommendations.append({
                "type": "organizational",
                "priority": "high",
                "message": "Consider implementing or reviewing on-call rotation schedules to distribute load more evenly"
            })
        
        if members_at_risk > 0:
            recommendations.append({
                "type": "interpersonal", 
                "priority": "high",
                "message": f"Schedule 1-on-1s with the {members_at_risk} team members at high risk"
            })
        
        # Pattern-based recommendations
        if members:
            # After-hours pattern with null safety
            after_hours_values = [
                m.get("metrics", {}).get("after_hours_percentage", 0) 
                for m in members if m and isinstance(m, dict)
            ]
            avg_after_hours = sum(after_hours_values) / len(after_hours_values) if after_hours_values else 0
            if avg_after_hours > 0.25:
                recommendations.append({
                    "type": "emotional_exhaustion",
                    "priority": "high",
                    "message": "Implement follow-the-sun support or adjust business hours coverage"
                })
            
            # Weekend pattern with null safety
            weekend_values = [
                m.get("metrics", {}).get("weekend_percentage", 0) 
                for m in members if m and isinstance(m, dict)
            ]
            avg_weekend = sum(weekend_values) / len(weekend_values) if weekend_values else 0
            if avg_weekend > 0.15:
                recommendations.append({
                    "type": "emotional_exhaustion", 
                    "priority": "medium",
                    "message": "Review weekend on-call compensation and rotation frequency"
                })
            
            # Workload distribution
            workload_variance = self._calculate_workload_variance(members)
            if workload_variance > 0.5:
                recommendations.append({
                    "type": "depersonalization",
                    "priority": "medium", 
                    "message": "Incident load is unevenly distributed - consider load balancing strategies"
                })
            
            # Response time with null safety
            response_values = [
                m.get("metrics", {}).get("avg_response_time_minutes", 0) 
                for m in members 
                if m and isinstance(m, dict) and m.get("metrics", {}).get("avg_response_time_minutes", 0) > 0
            ]
            avg_response = sum(response_values) / len(response_values) if response_values else 0
            if avg_response > 30:
                recommendations.append({
                    "type": "personal_accomplishment",
                    "priority": "medium",
                    "message": "Review alerting and escalation procedures to improve response times"
                })
        
        # Always include Christina Maslach-based recommendations
        if health_status in ["excellent", "good"]:
            recommendations.append({
                "type": "personal_accomplishment",
                "priority": "low", 
                "message": "Continue current practices and monitor for changes in team health metrics"
            })
        
        # Add specific Maslach dimension recommendations
        if members:
            high_burnout_members = [m for m in members if m.get("burnout_score", 0) >= 7.0]
            if high_burnout_members:
                recommendations.append({
                    "type": "emotional_exhaustion",
                    "priority": "high",
                    "message": "Provide stress management training and consider workload redistribution for high-burnout individuals"
                })
                
        # Add organizational support recommendations
        if members_at_risk > len(members) * 0.3:  # If more than 30% are at risk
            recommendations.append({
                "type": "organizational",
                "priority": "high", 
                "message": "Consider organizational changes: flexible schedules, mental health resources, and burnout prevention programs"
            })
        
        return recommendations
    
    def _parse_timestamp(self, timestamp: str) -> Optional[datetime]:
        """Parse ISO format timestamp."""
        try:
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            return None
    
    def _calculate_response_time(self, created_at: str, started_at: str) -> Optional[float]:
        """Calculate response time in minutes."""
        created = self._parse_timestamp(created_at)
        started = self._parse_timestamp(started_at)
        
        if created and started:
            return (started - created).total_seconds() / 60
        return None
    
    def _calculate_workload_variance(self, members: List[Dict[str, Any]]) -> float:
        """Calculate variance in workload distribution."""
        if not members:
            return 0
        
        incident_counts = [m.get("incident_count", 0) for m in members if m and isinstance(m, dict)]
        if not incident_counts:
            return 0
        
        mean = sum(incident_counts) / len(incident_counts)
        variance = sum((x - mean) ** 2 for x in incident_counts) / len(incident_counts)
        
        # Normalize by mean to get coefficient of variation
        return variance / mean if mean > 0 else 0
    
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
                }
            }
        
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
            }
        }
    
    async def _enhance_with_ai_analysis(
        self, 
        analysis_result: Dict[str, Any], 
        available_integrations: List[str]
    ) -> Dict[str, Any]:
        """
        Enhance traditional analysis with AI-powered insights.
        
        Args:
            analysis_result: Result from traditional burnout analysis
            available_integrations: List of available data integrations
            
        Returns:
            Enhanced analysis with AI insights
        """
        try:
            ai_analyzer = get_ai_burnout_analyzer()
            
            # Enhance each member analysis
            enhanced_members = []
            original_members = analysis_result.get("team_analysis", {}).get("members", [])
            
            for member in original_members:
                # Prepare member data for AI analysis
                member_data = {
                    "user_id": member.get("user_id"),
                    "user_name": member.get("user_name"), 
                    "incidents": self._format_incidents_for_ai(member),
                    "github_activity": member.get("github_activity"),
                    "slack_activity": member.get("slack_activity")
                }
                
                # Get AI enhancement
                enhanced_member = ai_analyzer.enhance_member_analysis(
                    member_data,
                    member,  # Traditional analysis
                    available_integrations
                )
                
                enhanced_members.append(enhanced_member)
            
            # Update members list
            if "team_analysis" not in analysis_result:
                analysis_result["team_analysis"] = {}
            analysis_result["team_analysis"]["members"] = enhanced_members
            
            # Generate team-level AI insights
            team_insights = ai_analyzer.generate_team_insights(
                enhanced_members,
                available_integrations
            )
            
            if team_insights.get("available"):
                analysis_result["ai_team_insights"] = team_insights
            
            # Add AI metadata
            analysis_result["ai_enhanced"] = True
            analysis_result["ai_enhancement_timestamp"] = datetime.utcnow().isoformat()
            
            logger.info(f"Successfully enhanced analysis with AI insights for {len(enhanced_members)} members")
            
        except Exception as e:
            logger.error(f"Failed to enhance analysis with AI: {e}")
            # Add error info but don't fail the main analysis
            analysis_result["ai_enhanced"] = False
            analysis_result["ai_error"] = str(e)
        
        return analysis_result
    
    def _format_incidents_for_ai(self, member_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Format incident data for AI analysis.
        
        Args:
            member_analysis: Member analysis containing incident metrics
            
        Returns:
            List of incident dictionaries formatted for AI
        """
        # Since we don't store raw incident data in member analysis,
        # we'll create approximated incident data based on the metrics
        incidents = []
        
        # Extract basic metrics
        incident_count = member_analysis.get("incident_count", 0)
        factors = member_analysis.get("factors", {})
        metrics = member_analysis.get("metrics", {})
        
        # Create approximated incident entries based on patterns
        # This is a simplified approach - in a full implementation,
        # we'd want to store the raw incident data
        
        if incident_count > 0:
            # Create sample incidents based on the analysis
            after_hours_rate = metrics.get("after_hours_percentage", 0)
            weekend_rate = metrics.get("weekend_percentage", 0)
            avg_response_time = metrics.get("avg_response_time_minutes", 15)
            
            for i in range(min(incident_count, 50)):  # Limit to 50 incidents for performance
                # Create approximated incident
                incident = {
                    "timestamp": datetime.utcnow().isoformat(),  # Placeholder
                    "response_time_minutes": avg_response_time + (i % 20 - 10),  # Add variance
                    "severity": "medium",  # Default
                    "created_at": datetime.utcnow().isoformat(),
                }
                
                # Add some patterns based on rates
                if i < incident_count * after_hours_rate:
                    # Mark as after-hours
                    incident["after_hours"] = True
                
                if i < incident_count * weekend_rate:
                    # Mark as weekend
                    incident["weekend"] = True
                
                incidents.append(incident)
        
        return incidents