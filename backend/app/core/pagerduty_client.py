"""
PagerDuty API client for fetching incident and user data.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import aiohttp
import pytz

logger = logging.getLogger(__name__)

class PagerDutyAPIClient:
    """Client for interacting with PagerDuty API."""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.pagerduty.com"
        self.headers = {
            "Authorization": f"Token token={api_token}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json"
        }
        
    async def test_connection(self) -> Dict[str, Any]:
        """Test the PagerDuty API connection and get account info."""
        try:
            # Test connection by fetching users (works with both user and account tokens)
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.base_url}/users",
                    headers=self.headers,
                    params={"limit": 1}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return {"valid": False, "error": f"HTTP {response.status}: {error_text}"}
                    
                    users_data = await response.json()
                    
                # Try to get current user info if it's a user token
                current_user = "Account Token"
                try:
                    async with session.get(
                        f"{self.base_url}/users/me",
                        headers=self.headers
                    ) as me_response:
                        if me_response.status == 200:
                            user_data = await me_response.json()
                            current_user = user_data.get("user", {}).get("name", "Unknown User")
                except:
                    # Account token - can't get current user
                    pass
                
                # Get organization info from first user's HTML URL if available
                org_name = "PagerDuty Account"
                users = users_data.get("users", [])
                if users:
                    html_url = users[0].get("html_url", "")
                    if html_url and "pagerduty.com" in html_url:
                        try:
                            # Extract subdomain from URL like https://orgname.pagerduty.com/...
                            subdomain = html_url.split("//")[1].split(".")[0]
                            if subdomain and subdomain != "www":
                                org_name = subdomain.title()
                        except (IndexError, AttributeError):
                            # Fallback to default name if URL parsing fails
                            pass
                
                # Get user and service counts
                services = await self.get_services(limit=1)
                
                # Count total users and services
                total_users = await self._get_total_count("users")
                total_services = await self._get_total_count("services")
                
                return {
                    "valid": True,
                    "account_info": {
                        "organization_name": org_name,
                        "total_users": total_users,
                        "total_services": total_services,
                        "current_user": current_user
                    }
                }
                
        except Exception as e:
            # Log with more specific error categorization
            error_msg = str(e)
            if "ssl" in error_msg.lower() or "cannot connect to host" in error_msg.lower():
                logger.warning(f"PagerDuty connection failed (network/SSL): {error_msg[:100]}...")
                return {"valid": False, "error": "Network connectivity issue - check internet connection"}
            elif "timeout" in error_msg.lower():
                logger.warning(f"PagerDuty connection timed out: {error_msg[:100]}...")
                return {"valid": False, "error": "Connection timeout - PagerDuty may be temporarily unavailable"}
            else:
                logger.error(f"PagerDuty connection test failed: {error_msg}")
                return {"valid": False, "error": error_msg}
    
    async def _get_total_count(self, resource: str) -> int:
        """Get total count of a resource (users, services, etc)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/{resource}",
                    headers=self.headers,
                    params={"limit": 100}  # Get more records to count if total is null
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        total = data.get("total")
                        if total is not None:
                            return total
                        else:
                            # If total is null, count the actual records
                            # This is a fallback for accounts where total isn't provided
                            records = data.get(resource, [])
                            count = len(records)
                            # If there are more records, we need to estimate
                            if data.get("more", False):
                                # Simple estimation: if we got 100 records and there are more,
                                # assume there are at least 100+ records
                                return count + 50  # Conservative estimate
                            return count
            return 0
        except:
            return 0
    
    async def get_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Fetch users from PagerDuty."""
        try:
            async with aiohttp.ClientSession() as session:
                all_users = []
                
                while True:
                    async with session.get(
                        f"{self.base_url}/users",
                        headers=self.headers,
                        params={
                            "limit": min(limit, 100),
                            "offset": offset,
                            "include[]": ["contact_methods", "teams"]
                        }
                    ) as response:
                        if response.status != 200:
                            logger.error(f"Failed to fetch users: HTTP {response.status}")
                            break
                            
                        data = await response.json()
                        users = data.get("users", [])
                        all_users.extend(users)
                        
                        # Check if we have more pages
                        if not data.get("more", False) or len(all_users) >= limit:
                            break
                            
                        offset += len(users)
                
                return all_users[:limit]
                
        except Exception as e:
            logger.error(f"Error fetching PagerDuty users: {e}")
            return []
    
    async def get_incidents(
        self, 
        since: datetime,
        until: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Fetch incidents from PagerDuty within a date range."""
        try:
            if until is None:
                until = datetime.now(pytz.UTC)
                
            # Convert to ISO format with timezone
            since_str = since.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            until_str = until.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            async with aiohttp.ClientSession() as session:
                all_incidents = []
                offset = 0
                max_requests = 150  # Circuit breaker - max 150 requests (15000 incidents at 100 per page)
                request_count = 0
                
                while len(all_incidents) < limit and request_count < max_requests:
                    logger.info(f"Fetching PagerDuty incidents: offset={offset}, collected={len(all_incidents)}/{limit}")
                    
                    # Add timeout to prevent hanging
                    timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout per request
                    async with session.get(
                        f"{self.base_url}/incidents",
                        headers=self.headers,
                        timeout=timeout,
                        params={
                            "since": since_str,
                            "until": until_str,
                            "limit": min(100, limit - len(all_incidents)),
                            "offset": offset,
                            "include[]": ["users", "services", "teams", "escalation_policies"],
                            "statuses[]": ["triggered", "acknowledged", "resolved"]
                        }
                    ) as response:
                        request_count += 1
                        
                        if response.status != 200:
                            logger.error(f"Failed to fetch incidents: HTTP {response.status}")
                            break
                            
                        data = await response.json()
                        incidents = data.get("incidents", [])
                        all_incidents.extend(incidents)
                        
                        logger.info(f"PagerDuty: Fetched {len(incidents)} incidents in this batch")
                        
                        # Check if we have more pages
                        if not data.get("more", False) or len(incidents) == 0:
                            logger.info(f"PagerDuty: No more incidents to fetch")
                            break
                            
                        offset += len(incidents)
                
                if request_count >= max_requests:
                    logger.warning(f"PagerDuty: Hit request limit ({max_requests}), stopping incident fetch")
                
                logger.info(f"PagerDuty: Completed incident fetch - total incidents: {len(all_incidents)}")
                return all_incidents
                
        except asyncio.TimeoutError:
            logger.error(f"PagerDuty incident fetch timed out after collecting {len(all_incidents) if 'all_incidents' in locals() else 0} incidents")
            return all_incidents if 'all_incidents' in locals() else []
        except Exception as e:
            logger.error(f"Error fetching PagerDuty incidents: {e}")
            return all_incidents if 'all_incidents' in locals() else []
    
    async def get_services(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch services from PagerDuty."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/services",
                    headers=self.headers,
                    params={"limit": limit}
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch services: HTTP {response.status}")
                        return []
                        
                    data = await response.json()
                    return data.get("services", [])
                    
        except Exception as e:
            logger.error(f"Error fetching PagerDuty services: {e}")
            return []
    
    async def collect_analysis_data(self, days_back: int = 30) -> Dict[str, Any]:
        """Collect all data needed for burnout analysis."""
        logger.info(f"Starting PagerDuty data collection for last {days_back} days...")
        
        try:
            # Test connection first
            connection_test = await self.test_connection()
            if not connection_test["valid"]:
                raise Exception(f"Connection test failed: {connection_test.get('error', 'Unknown error')}")
            
            # Calculate date range
            end_date = datetime.now(pytz.UTC)
            start_date = end_date - timedelta(days=days_back)
            
            # Dynamic incident limits based on time range (similar to Rootly)
            incident_limits_by_range = {
                7: 2000,   # 7-day: up to 2000 incidents
                14: 3000,  # 14-day: up to 3000 incidents  
                30: 5000,  # 30-day: up to 5000 incidents
                60: 7000,  # 60-day: up to 7000 incidents
                90: 10000, # 90-day: up to 10000 incidents
                180: 15000 # 180-day (6 months): up to 15000 incidents
            }
            
            # Find appropriate limit for the time range
            incident_limit = 10000  # Default fallback
            for range_days in sorted(incident_limits_by_range.keys()):
                if days_back <= range_days:
                    incident_limit = incident_limits_by_range[range_days]
                    break
            
            logger.info(f"📊 PagerDuty: Using incident limit of {incident_limit} for {days_back}-day analysis")
            
            # Collect users and incidents in parallel
            users_task = self.get_users(limit=1000)
            incidents_task = self.get_incidents(since=start_date, until=end_date, limit=incident_limit)
            
            users = await users_task
            incidents = await incidents_task
            
            # Validate data
            if not users:
                raise Exception("No users found - check API permissions")
            
            # Count incidents by urgency/priority (PagerDuty equivalent of severity)
            urgency_counts = {
                "sev1_count": 0,  # P1/Critical = SEV1
                "sev2_count": 0,  # P2/High = SEV2
                "sev3_count": 0,  # P3/Medium = SEV3  
                "sev4_count": 0,  # P4/Low = SEV4
                "sev5_count": 0   # P5/Info = SEV5
            }
            
            # Process incidents to count urgencies
            for i, incident in enumerate(incidents):
                try:
                    # Debug: Log incident structure for first few incidents
                    if i < 3:
                        logger.info(f"DEBUG PagerDuty incident #{i}: urgency='{incident.get('urgency')}', priority='{incident.get('priority')}', title='{incident.get('title', 'no title')[:50]}'")
                        if incident.get('priority'):
                            logger.info(f"  Priority object: {incident['priority']}")
                    
                    # PagerDuty uses urgency field (high, low)
                    urgency = incident.get("urgency", "low").lower()
                    
                    # Check priority first for P0/critical classification
                    priority = incident.get("priority")
                    priority_name = ""
                    if priority and isinstance(priority, dict):
                        priority_name = priority.get("summary", "").lower()
                        # Also check 'name' field in case summary doesn't exist
                        if not priority_name:
                            priority_name = priority.get("name", "").lower()
                    
                    # Map PagerDuty priorities P1-P5 to severity levels SEV1-5
                    mapped_severity = None
                    if "p1" in priority_name or "critical" in priority_name:
                        urgency_counts["sev1_count"] += 1
                        mapped_severity = "sev1 (p1/critical)"
                    elif "p2" in priority_name or "high" in priority_name:
                        urgency_counts["sev2_count"] += 1
                        mapped_severity = "sev2 (p2/high)"
                    elif "p3" in priority_name or "medium" in priority_name:
                        urgency_counts["sev3_count"] += 1
                        mapped_severity = "sev3 (p3/medium)"
                    elif "p4" in priority_name or "low" in priority_name:
                        urgency_counts["sev4_count"] += 1
                        mapped_severity = "sev4 (p4/low)"
                    elif "p5" in priority_name or "info" in priority_name:
                        urgency_counts["sev5_count"] += 1
                        mapped_severity = "sev5 (p5/info)"
                    elif urgency == "high":
                        # High urgency without specific priority = SEV1
                        urgency_counts["sev1_count"] += 1
                        mapped_severity = "sev1 (high urgency, no priority)"
                    elif urgency == "low":
                        # Low urgency without specific priority = SEV4
                        urgency_counts["sev4_count"] += 1
                        mapped_severity = "sev4 (low urgency, no priority)"
                    else:
                        # Unknown urgency/priority defaults to SEV5
                        urgency_counts["sev5_count"] += 1
                        mapped_severity = f"sev5 (unknown: urgency='{urgency}', priority='{priority_name}')"
                    
                    # Debug: Log mapping for first few incidents
                    if i < 3:
                        logger.info(f"  → Mapped to {mapped_severity}")
                        
                except Exception as e:
                    logger.debug(f"Error counting urgency for incident: {e}")
                    # Default to sev5 on error
                    urgency_counts["sev5_count"] += 1
            
            # Debug: Log final severity breakdown
            total_mapped = sum(urgency_counts.values())
            logger.info(f"PagerDuty severity mapping summary ({total_mapped} incidents):")
            for sev, count in urgency_counts.items():
                logger.info(f"  {sev}: {count} incidents ({count/total_mapped*100:.1f}%)" if total_mapped > 0 else f"  {sev}: {count} incidents")
            
            # Normalize data to common format for burnout analysis
            normalized_data = self.normalize_to_common_format(incidents, users)
            
            # Process and return data
            processed_data = {
                "users": normalized_data["users"],
                "incidents": normalized_data["incidents"],
                "collection_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "days_analyzed": days_back,
                    "total_users": len(users),
                    "total_incidents": len(incidents),
                    "severity_breakdown": urgency_counts,  # Use same key as Rootly for consistency
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    }
                }
            }
            
            logger.info(f"PagerDuty data collection completed: {len(users)} users, {len(incidents)} incidents")
            return processed_data
            
        except Exception as e:
            logger.error(f"PagerDuty data collection failed: {e}")
            # Return minimal data structure instead of failing completely
            return {
                "users": [],
                "incidents": [],
                "collection_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "days_analyzed": days_back,
                    "total_users": 0,
                    "total_incidents": 0,
                    "severity_breakdown": {
                        "sev1_count": 0,
                        "sev2_count": 0,
                        "sev3_count": 0,
                        "sev4_count": 0,
                        "sev5_count": 0
                    },
                    "error": str(e),
                    "date_range": {
                        "start": (datetime.now() - timedelta(days=days_back)).isoformat(),
                        "end": datetime.now().isoformat()
                    }
                }
            }
    
    def normalize_to_common_format(
        self, 
        incidents: List[Dict[str, Any]], 
        users: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Convert PagerDuty data to common format for burnout analysis."""
        
        # Normalize users
        normalized_users = []
        for user in users:
            normalized_users.append({
                "id": user.get("id"),
                "name": user.get("name") or user.get("summary", "Unknown"),
                "email": user.get("email", ""),
                "timezone": user.get("time_zone", "UTC"),
                "role": user.get("role", "user"),
                "source": "pagerduty"
            })
        
        # Normalize incidents  
        normalized_incidents = []
        for incident in incidents:
            # Extract assignee information
            assignees = incident.get("assignments", [])
            assigned_user = None
            if assignees:
                assigned_user = assignees[0].get("assignee", {})
            
            # Determine severity from urgency/priority (PagerDuty P1-P5 → SEV1-5)
            urgency = incident.get("urgency", "low")
            priority = incident.get("priority")
            priority_name = ""
            if priority and isinstance(priority, dict):
                priority_name = priority.get("summary", "").lower()
            
            # Map PagerDuty priorities P1-P5 to severity levels SEV1-5
            if "p1" in priority_name or "critical" in priority_name:
                severity = "sev1"
            elif "p2" in priority_name or "high" in priority_name:
                severity = "sev2"
            elif "p3" in priority_name or "medium" in priority_name:
                severity = "sev3"
            elif "p4" in priority_name or "low" in priority_name:
                severity = "sev4"
            elif "p5" in priority_name or "info" in priority_name:
                severity = "sev5"
            elif urgency == "high":
                # High urgency without specific priority = SEV1
                severity = "sev1"
            elif urgency == "low":
                # Low urgency without specific priority = SEV4
                severity = "sev4"
            else:
                # Unknown urgency/priority defaults to SEV5
                severity = "sev5"
            
            # Calculate duration
            created_at = incident.get("created_at")
            resolved_at = incident.get("resolved_at")
            acknowledged_at = incident.get("acknowledged_at")
            
            duration_minutes = None
            if created_at and resolved_at:
                try:
                    start = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(resolved_at.replace('Z', '+00:00'))
                    duration_minutes = (end - start).total_seconds() / 60
                except:
                    pass
            
            time_to_ack_minutes = None
            if created_at and acknowledged_at:
                try:
                    start = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    ack = datetime.fromisoformat(acknowledged_at.replace('Z', '+00:00'))
                    time_to_ack_minutes = (ack - start).total_seconds() / 60
                except:
                    pass
            
            normalized_incidents.append({
                "id": incident.get("id"),
                "title": incident.get("title", "Untitled Incident"),
                "description": incident.get("description", ""),
                "status": incident.get("status", "unknown"),
                "severity_name": severity,
                "severity_level": urgency,
                "created_at": created_at,
                "resolved_at": resolved_at,
                "acknowledged_at": acknowledged_at,
                "duration_minutes": duration_minutes,
                "time_to_acknowledge_minutes": time_to_ack_minutes,
                "assigned_to": {
                    "id": assigned_user.get("id") if assigned_user else None,
                    "name": (assigned_user.get("name") or assigned_user.get("summary")) if assigned_user else None,
                    "email": assigned_user.get("email") if assigned_user else None
                } if assigned_user else None,
                "service": incident.get("service", {}).get("summary", "Unknown Service"),
                "source": "pagerduty",
                "url": incident.get("html_url"),
                "raw_data": incident  # Include raw incident data for enhanced assignment logic
            })
        
        return {
            "users": normalized_users,
            "incidents": normalized_incidents,
            "metadata": {
                "source": "pagerduty",
                "incident_count": len(normalized_incidents),
                "user_count": len(normalized_users)
            }
        }


class PagerDutyDataCollector:
    """Collects and processes data from PagerDuty for burnout analysis."""
    
    def __init__(self, api_token: str):
        self.client = PagerDutyAPIClient(api_token)
        
    async def collect_all_data(self, days_back: int = 30) -> Dict[str, Any]:
        """Collect all necessary data for burnout analysis."""
        logger.info(f"Starting PagerDuty data collection for last {days_back} days")
        
        # Calculate date range
        until = datetime.now(pytz.UTC)
        since = until - timedelta(days=days_back)
        
        # Fetch data in parallel (no limits for complete data collection)
        users_task = self.client.get_users(limit=1000)
        incidents_task = self.client.get_incidents(since=since, until=until)
        
        users, incidents = await asyncio.gather(users_task, incidents_task)
        
        logger.info(f"Collected {len(users)} users and {len(incidents)} incidents from PagerDuty")
        
        # Normalize to common format
        normalized_data = self.client.normalize_to_common_format(incidents, users)
        
        # Add collection metadata
        normalized_data["collection_metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "days_analyzed": days_back,
            "date_range": {
                "start": since.isoformat(),
                "end": until.isoformat()
            }
        }
        
        return normalized_data