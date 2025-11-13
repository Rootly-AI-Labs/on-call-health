"""
Data collection module for gathering Rootly incident and user data.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pytz

from mcp_client import RootlyMCPClient

logger = logging.getLogger(__name__)


class RootlyDataCollector:
    """Collects and processes data from Rootly via MCP server."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = RootlyMCPClient(config)
        self.analysis_config = config.get("analysis", {})
        
    async def collect_all_data(self) -> Dict[str, Any]:
        """Collect all necessary data for burnout analysis."""
        logger.info("Starting data collection...")
        
        async with self.client.connect() as session:
            # Collect base data
            users = await self.client.get_users(limit=200)
            
            days_to_analyze = self.analysis_config.get("days_to_analyze", 30)
            incidents = await self.client.get_all_incidents(days_back=days_to_analyze)
            
            # Validate data collection succeeded
            if len(users) == 0:
                raise RuntimeError("❌ Failed to fetch users from Rootly. This likely indicates:\n" +
                                 "  • Invalid or expired API token\n" +
                                 "  • 404 error - API endpoint not accessible\n" +
                                 "  • Network connectivity issues\n" +
                                 "  • Insufficient permissions for your API token")
            
            if len(incidents) == 0:
                logger.warning(f"⚠️  No incidents found in the last {days_to_analyze} days. This may be normal for quiet periods or indicate API access issues.")
            
            logger.info(f"Collected {len(users)} users, {len(incidents)} incidents")
            
            # Process and enrich data
            processed_data = {
                "users": self._process_users(users),
                "incidents": self._process_incidents(incidents),
                "user_incident_mapping": self._map_users_to_incidents(users, incidents),
                "collection_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "days_analyzed": days_to_analyze,
                    "total_users": len(users),
                    "total_incidents": len(incidents),
                    "date_range": {
                        "start": (datetime.now() - timedelta(days=days_to_analyze)).isoformat(),
                        "end": datetime.now().isoformat()
                    }
                }
            }
            
            return processed_data
    
    def _process_users(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and normalize user data."""
        processed = []
        
        for user in users:
            attrs = user.get("attributes", {})
            processed_user = {
                "id": user.get("id"),
                "name": attrs.get("full_name", attrs.get("name", "Unknown")),
                "email": attrs.get("email"),
                "timezone": attrs.get("time_zone", "UTC"),
                "first_name": attrs.get("first_name"),
                "last_name": attrs.get("last_name"),
                "slack_id": attrs.get("slack_id"),
                "created_at": attrs.get("created_at"),
                "updated_at": attrs.get("updated_at"),
            }
            processed.append(processed_user)
        
        return processed
    
    
    def _process_incidents(self, incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and normalize incident data."""
        processed = []
        
        for incident in incidents:
            attrs = incident.get("attributes", {})
            
            # Extract severity information
            severity_info = attrs.get("severity", {})
            if isinstance(severity_info, dict) and "data" in severity_info:
                severity_data = severity_info["data"]
                severity_name = severity_data.get("attributes", {}).get("name", "Unknown")
                severity_level = severity_data.get("attributes", {}).get("severity", "low")
            else:
                severity_name = "Unknown"
                severity_level = "low"
            
            processed_incident = {
                "id": incident.get("id"),
                "title": attrs.get("title"),
                "summary": attrs.get("summary"),
                "status": attrs.get("status"),
                "severity_name": severity_name,
                "severity_level": severity_level,
                "created_at": attrs.get("created_at"),
                "started_at": attrs.get("started_at"),
                "resolved_at": attrs.get("resolved_at"),
                "mitigated_at": attrs.get("mitigated_at"),
                "acknowledged_at": attrs.get("acknowledged_at"),
                "sequential_id": attrs.get("sequential_id"),
                "url": attrs.get("url"),
                "slack_channel_id": attrs.get("slack_channel_id"),
                "resolution_message": attrs.get("resolution_message"),
                
                # Extract user involvement
                "created_by": self._extract_user_info(attrs.get("user")),
                "started_by": self._extract_user_info(attrs.get("started_by")),
                "resolved_by": self._extract_user_info(attrs.get("resolved_by")),
                
                # Calculate durations
                "duration_minutes": self._calculate_duration(
                    attrs.get("started_at"), 
                    attrs.get("resolved_at")
                ),
                "time_to_start_minutes": self._calculate_duration(
                    attrs.get("created_at"), 
                    attrs.get("started_at")
                ),
                "time_to_acknowledge_minutes": self._calculate_duration(
                    attrs.get("created_at"), 
                    attrs.get("acknowledged_at")
                ),
                
                # Relationship data
                "roles": self._extract_relationship_data(incident, "roles"),
                "services": self._extract_relationship_data(incident, "services"),
                "teams": self._extract_relationship_data(incident, "teams"),
                "events": self._extract_relationship_data(incident, "events")
            }
            
            processed.append(processed_incident)
        
        return processed
    
    def _extract_user_info(self, user_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract user information from nested user data."""
        if not user_data or "data" not in user_data:
            return None
        
        user = user_data["data"]
        attrs = user.get("attributes", {})
        
        return {
            "id": user.get("id"),
            "name": attrs.get("full_name", attrs.get("name")),
            "email": attrs.get("email"),
            "slack_id": attrs.get("slack_id")
        }
    
    
    def _extract_relationship_data(self, incident: Dict[str, Any], relationship_name: str) -> List[str]:
        """Extract relationship IDs from incident data."""
        relationships = incident.get("relationships", {})
        relationship = relationships.get(relationship_name, {})
        
        if "data" in relationship:
            data = relationship["data"]
            if isinstance(data, list):
                return [item.get("id") for item in data if item.get("id")]
            elif isinstance(data, dict):
                return [data.get("id")] if data.get("id") else []
        
        return []
    
    def _calculate_duration(self, start_time: Optional[str], end_time: Optional[str]) -> Optional[float]:
        """Calculate duration in minutes between two timestamps."""
        if not start_time or not end_time:
            return None
        
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            return (end - start).total_seconds() / 60
        except Exception as e:
            logger.warning(f"Error calculating duration: {e}")
            return None
    
    def _map_users_to_incidents(
        self, 
        users: List[Dict[str, Any]], 
        incidents: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Create mapping of user IDs to incident IDs they were involved in."""
        user_incidents = {}
        
        # Initialize mapping for all users
        for user in users:
            user_id = user.get("id")
            if user_id:
                user_incidents[user_id] = []
        
        # Map incidents to users based on roles
        for incident in incidents:
            incident_id = incident.get("id")
            if not incident_id:
                continue
            
            attrs = incident.get("attributes", {})
            
            # Check various user involvement fields
            user_fields = ["user", "started_by", "resolved_by"]
            for field in user_fields:
                user_data = attrs.get(field)
                if user_data and "data" in user_data:
                    user_id = user_data["data"].get("id")
                    if user_id and user_id in user_incidents:
                        if incident_id not in user_incidents[user_id]:
                            user_incidents[user_id].append(incident_id)
            
            # TODO: Add role assignments when available in the data
            # This would require additional API calls to get role details
        
        return user_incidents
    
    def calculate_after_hours_incidents(
        self, 
        incidents: List[Dict[str, Any]], 
        user_timezone: str
    ) -> List[str]:
        """Calculate which incidents occurred during after-hours for a user."""
        business_hours = self.analysis_config.get("business_hours", {"start": 9, "end": 17})
        after_hours_incidents = []
        
        try:
            tz = pytz.timezone(user_timezone)
        except Exception:
            tz = pytz.UTC
        
        for incident in incidents:
            attrs = incident.get("attributes", {})
            created_at = attrs.get("created_at")
            
            if created_at:
                try:
                    # Parse the timestamp and convert to user's timezone
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    local_dt = dt.astimezone(tz)
                    
                    # Check if it's outside business hours
                    hour = local_dt.hour
                    is_weekend = local_dt.weekday() >= 5  # Saturday = 5, Sunday = 6
                    
                    if (is_weekend or 
                        hour < business_hours["start"] or 
                        hour >= business_hours["end"]):
                        after_hours_incidents.append(incident.get("id"))
                        
                except Exception as e:
                    logger.warning(f"Error processing timestamp {created_at}: {e}")
        
        return after_hours_incidents


async def main():
    """Test data collection."""
    # Load config
    config_path = "../config/config.example.json"
    with open(config_path) as f:
        config = json.load(f)
    
    collector = RootlyDataCollector(config)
    data = await collector.collect_all_data()
    
    # Save collected data
    output_path = "../output/collected_data.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Data collected and saved to {output_path}")
    print(f"Users: {len(data['users'])}")
    print(f"Incidents: {len(data['incidents'])}")


if __name__ == "__main__":
    import os
    asyncio.run(main())