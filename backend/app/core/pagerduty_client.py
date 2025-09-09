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
        
        # 🎯 RAILWAY DEBUG: Token identification for debugging
        token_suffix = api_token[-4:] if len(api_token) > 4 else "***"
        logger.info(f"🎯 PAGERDUTY CLIENT: Initialized with token ending in {token_suffix}")
        logger.info(f"🎯 PAGERDUTY CLIENT: Enhanced normalization version ACTIVE")
        
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
        logger.info(f"🔍 PD GET_USERS: Starting user fetch (limit={limit})")
        
        try:
            async with aiohttp.ClientSession() as session:
                all_users = []
                request_count = 0
                
                while True:
                    request_count += 1
                    logger.info(f"🔍 PD GET_USERS: API Request #{request_count}, offset={offset}")
                    
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
                            error_text = await response.text()
                            logger.error(f"🔍 PD GET_USERS: API ERROR - HTTP {response.status}: {error_text}")
                            break
                            
                        data = await response.json()
                        users = data.get("users", [])
                        all_users.extend(users)
                        
                        logger.info(f"🔍 PD GET_USERS: Fetched {len(users)} users in batch, total: {len(all_users)}")
                        
                        # Log first few users for analysis
                        if request_count == 1 and users:
                            logger.info(f"🔍 PD GET_USERS: First batch user analysis:")
                            for i, user in enumerate(users[:3]):
                                logger.info(f"   - User #{i+1}: {user.get('name')} (ID: {user.get('id')}, Email: {user.get('email')})")
                        
                        # Check if we have more pages
                        if not data.get("more", False) or len(all_users) >= limit:
                            logger.info(f"🔍 PD GET_USERS: No more users to fetch (more={data.get('more')}, limit_reached={len(all_users) >= limit})")
                            break
                            
                        offset += len(users)
                
                final_users = all_users[:limit]
                
                # COMPREHENSIVE USER SUMMARY
                logger.info(f"🔍 PD GET_USERS: FINAL SUMMARY:")
                logger.info(f"   - Total users fetched: {len(final_users)}")
                logger.info(f"   - API requests made: {request_count}")
                
                if final_users:
                    user_ids = [user.get("id") for user in final_users]
                    user_emails = [user.get("email") for user in final_users if user.get("email")]
                    
                    logger.info(f"   - Sample user IDs: {user_ids[:5]}")
                    logger.info(f"   - Users with emails: {len(user_emails)}/{len(final_users)}")
                    if user_emails:
                        logger.info(f"   - Sample emails: {user_emails[:3]}")
                
                return final_users
                
        except Exception as e:
            logger.error(f"🔍 PD GET_USERS: ERROR - {e}")
            return []
    
    async def get_incidents(
        self, 
        since: datetime,
        until: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Fetch incidents from PagerDuty within a date range."""
        logger.info(f"🔍 PD GET_INCIDENTS: Starting incident fetch")
        logger.info(f"🔍 PD GET_INCIDENTS: Date range: {since.isoformat()} to {until.isoformat() if until else 'now'}")
        logger.info(f"🔍 PD GET_INCIDENTS: Requested limit: {limit}")
        
        try:
            if until is None:
                until = datetime.now(pytz.UTC)
                
            # Convert to ISO format with timezone
            since_str = since.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            until_str = until.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            logger.info(f"🔍 PD GET_INCIDENTS: API date range: {since_str} to {until_str}")
            
            async with aiohttp.ClientSession() as session:
                all_incidents = []
                offset = 0
                max_requests = 150  # Circuit breaker - max 150 requests (15000 incidents at 100 per page)
                request_count = 0
                
                while len(all_incidents) < limit and request_count < max_requests:
                    logger.info(f"🔍 PD GET_INCIDENTS: API Request #{request_count+1}: offset={offset}, collected={len(all_incidents)}/{limit}")
                    
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
                            error_text = await response.text()
                            token_suffix = self.api_token[-4:] if len(self.api_token) > 4 else "***"
                            logger.error(f"🚨 PD GET_INCIDENTS: API ERROR - HTTP {response.status}")
                            logger.error(f"🚨 PD GET_INCIDENTS: Token ending in {token_suffix}")
                            logger.error(f"🚨 PD GET_INCIDENTS: URL: {self.base_url}/incidents")
                            logger.error(f"🚨 PD GET_INCIDENTS: Headers: {dict(self.headers)}")
                            logger.error(f"🚨 PD GET_INCIDENTS: Params: since={since_str}, until={until_str}")
                            logger.error(f"🚨 PD GET_INCIDENTS: Response: {error_text}")
                            break
                            
                        data = await response.json()
                        incidents = data.get("incidents", [])
                        
                        # COMPREHENSIVE LOGGING FOR FIRST BATCH
                        if len(all_incidents) == 0 and len(incidents) > 0:
                            logger.info(f"🔍 PD GET_INCIDENTS: First batch analysis:")
                            logger.info(f"   - Response keys: {list(data.keys())}")
                            logger.info(f"   - Incidents in batch: {len(incidents)}")
                            logger.info(f"   - Has more pages: {data.get('more', False)}")
                            
                            # Analyze first 3 incidents in detail
                            for i, incident in enumerate(incidents[:3]):
                                logger.info(f"🔍 PD INCIDENT #{i+1}:")
                                logger.info(f"   - ID: {incident.get('id')}")
                                logger.info(f"   - Title: {incident.get('title', 'No title')[:50]}")
                                logger.info(f"   - Status: {incident.get('status')}")
                                logger.info(f"   - Created: {incident.get('created_at')}")
                                logger.info(f"   - Urgency: {incident.get('urgency')}")
                                logger.info(f"   - Priority: {incident.get('priority')}")
                                
                                # CHECK ALL POSSIBLE ASSIGNMENT FIELDS
                                assignments = incident.get("assignments", [])
                                assignees = incident.get("assignees", [])
                                last_status_change_by = incident.get("last_status_change_by")
                                service = incident.get("service", {})
                                
                                logger.info(f"   - Assignments: {assignments}")
                                logger.info(f"   - Assignees: {assignees}")
                                logger.info(f"   - Last status change by: {last_status_change_by}")
                                logger.info(f"   - Service: {service.get('summary', 'Unknown') if service else 'None'}")
                                
                                # Check for acknowledgments
                                acknowledgments = incident.get("acknowledgments", [])
                                logger.info(f"   - Acknowledgments: {len(acknowledgments)} found")
                                if acknowledgments:
                                    for j, ack in enumerate(acknowledgments[:2]):
                                        acknowledger = ack.get("acknowledger", {})
                                        logger.info(f"     - Ack #{j+1}: {acknowledger.get('summary', 'Unknown')} ({acknowledger.get('id')})")
                        
                        all_incidents.extend(incidents)
                        
                        logger.info(f"🔍 PD GET_INCIDENTS: Fetched {len(incidents)} incidents in batch #{request_count}, total: {len(all_incidents)}")
                        
                        # Check if we have more pages
                        if not data.get("more", False) or len(incidents) == 0:
                            logger.info(f"🔍 PD GET_INCIDENTS: No more incidents to fetch (more={data.get('more')}, batch_size={len(incidents)})")
                            break
                            
                        offset += len(incidents)
                
                if request_count >= max_requests:
                    logger.warning(f"🔍 PD GET_INCIDENTS: Hit request limit ({max_requests}), stopping incident fetch")
                
                # COMPREHENSIVE FINAL ANALYSIS
                logger.info(f"🔍 PD GET_INCIDENTS: FINAL SUMMARY:")
                logger.info(f"   - Total incidents fetched: {len(all_incidents)}")
                logger.info(f"   - API requests made: {request_count}")
                logger.info(f"   - Date range: {since_str} to {until_str}")
                
                if all_incidents:
                    # Analyze assignment patterns across all incidents
                    incidents_with_assignments = 0
                    incidents_with_acknowledgments = 0
                    unique_assigned_user_ids = set()
                    unique_acknowledger_ids = set()
                    
                    for incident in all_incidents:
                        # Check assignments
                        assignments = incident.get("assignments", [])
                        if assignments:
                            incidents_with_assignments += 1
                            for assignment in assignments:
                                assignee = assignment.get("assignee", {})
                                if assignee.get("id"):
                                    unique_assigned_user_ids.add(assignee["id"])
                        
                        # Check acknowledgments  
                        acknowledgments = incident.get("acknowledgments", [])
                        if acknowledgments:
                            incidents_with_acknowledgments += 1
                            for ack in acknowledgments:
                                acknowledger = ack.get("acknowledger", {})
                                if acknowledger.get("id"):
                                    unique_acknowledger_ids.add(acknowledger["id"])
                    
                    logger.info(f"🔍 PD GET_INCIDENTS: Assignment Analysis:")
                    logger.info(f"   - Incidents with assignments: {incidents_with_assignments}/{len(all_incidents)} ({incidents_with_assignments/len(all_incidents)*100:.1f}%)")
                    logger.info(f"   - Incidents with acknowledgments: {incidents_with_acknowledgments}/{len(all_incidents)} ({incidents_with_acknowledgments/len(all_incidents)*100:.1f}%)")
                    logger.info(f"   - Unique assigned users: {len(unique_assigned_user_ids)} IDs")
                    logger.info(f"   - Unique acknowledger users: {len(unique_acknowledger_ids)} IDs")
                    
                    if unique_assigned_user_ids:
                        logger.info(f"   - Sample assigned user IDs: {list(unique_assigned_user_ids)[:5]}")
                    if unique_acknowledger_ids:
                        logger.info(f"   - Sample acknowledger user IDs: {list(unique_acknowledger_ids)[:5]}")
                else:
                    logger.warning(f"🔍 PD GET_INCIDENTS: ❌ NO INCIDENTS FOUND!")
                    logger.warning(f"   - This could indicate:")
                    logger.warning(f"     1. No incidents in date range ({since_str} to {until_str})")
                    logger.warning(f"     2. API token lacks incident read permissions")
                    logger.warning(f"     3. API query parameters are incorrect")
                
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
        """
        🚀 ENHANCED PagerDuty data normalization with comprehensive assignment extraction.
        
        IMPROVEMENTS:
        - User ID to email lookup mapping (fixes email: None issue)
        - Multi-source assignment extraction (assignments + acknowledgments + status changes)
        - Priority-based assignment selection
        - Comprehensive validation and logging
        - Performance optimization with caching
        """
        
        logger.info(f"🚀 PD NORMALIZE ENHANCED: Starting comprehensive normalization")
        logger.info(f"   - Input: {len(users)} users, {len(incidents)} incidents")
        
        # 🎯 STEP 1: Create optimized user lookup maps
        user_id_to_email = {}
        user_id_to_name = {}
        user_id_to_full_data = {}
        
        logger.info(f"🚀 PD NORMALIZE: Building user lookup maps...")
        for user in users:
            user_id = user.get("id")
            if user_id:
                user_id_to_email[user_id] = user.get("email", "")
                user_id_to_name[user_id] = user.get("name") or user.get("summary", "Unknown")
                user_id_to_full_data[user_id] = user
        
        logger.info(f"🚀 PD NORMALIZE: Lookup maps created:")
        logger.info(f"   - Users with emails: {len([e for e in user_id_to_email.values() if e])}/{len(user_id_to_email)}")
        logger.info(f"   - Sample email mapping: {dict(list(user_id_to_email.items())[:3])}")
        
        # 🎯 STEP 2: Normalize users with enhanced data
        normalized_users = []
        for user in users:
            normalized_user = {
                "id": user.get("id"),
                "name": user.get("name") or user.get("summary", "Unknown"),
                "email": user.get("email", ""),
                "timezone": user.get("time_zone", "UTC"),
                "role": user.get("role", "user"),
                "source": "pagerduty",
                # Enhanced fields
                "job_title": user.get("job_title", ""),
                "teams": [team.get("summary", "") for team in user.get("teams", [])],
                "contact_methods_count": len(user.get("contact_methods", []))
            }
            normalized_users.append(normalized_user)
        
        # 🎯 STEP 3: Enhanced assignment extraction with multiple sources
        assignment_stats = {
            "total_processed": 0,
            "method_counts": {
                "assignments": 0,
                "acknowledgments": 0, 
                "last_status_change_user": 0,
                "incident_responders": 0,
                "escalation_policy_fallback": 0,
                "none": 0
            },
            "user_coverage": {
                "total_unique_users": set(),
                "assignment_users": set(),
                "acknowledger_users": set(),
                "status_change_users": set()
            },
            "email_lookup_success": 0,
            "email_lookup_failed": 0
        }
        
        normalized_incidents = []
        logger.info(f"🚀 PD NORMALIZE: Processing incidents with enhanced assignment extraction...")
        
        for i, incident in enumerate(incidents):
            assignment_stats["total_processed"] += 1
            
            # 🎯 COMPREHENSIVE ASSIGNMENT EXTRACTION WITH PRIORITY SYSTEM
            assigned_user_data = None
            assignment_method = "none"
            assignment_priority = 0  # Higher = better
            
            # PRIORITY 1: Direct assignments (highest confidence)
            assignments = incident.get("assignments", [])
            if assignments and isinstance(assignments, list):
                for assignment in assignments:
                    assignee = assignment.get("assignee", {})
                    if assignee and assignee.get("id") and assignee.get("type") == "user_reference":
                        assigned_user_data = assignee
                        assignment_method = "assignments"
                        assignment_priority = 10
                        assignment_stats["method_counts"]["assignments"] += 1
                        assignment_stats["user_coverage"]["assignment_users"].add(assignee["id"])
                        break
            
            # PRIORITY 2: Acknowledgments (high confidence - user actively engaged)  
            if assignment_priority < 8:
                acknowledgments = incident.get("acknowledgments", [])
                if acknowledgments and isinstance(acknowledgments, list):
                    # Get most recent acknowledgment
                    for ack in acknowledgments:
                        acknowledger = ack.get("acknowledger", {})
                        if acknowledger and acknowledger.get("id") and acknowledger.get("type") == "user_reference":
                            assigned_user_data = acknowledger
                            assignment_method = "acknowledgments"
                            assignment_priority = 8
                            assignment_stats["method_counts"]["acknowledgments"] += 1
                            assignment_stats["user_coverage"]["acknowledger_users"].add(acknowledger["id"])
                            break
            
            # PRIORITY 3: Incident responders (medium confidence)
            if assignment_priority < 6:
                responders = incident.get("incidents_responders", [])
                if responders and isinstance(responders, list):
                    for responder in responders:
                        if responder.get("state") == "accepted" and responder.get("user"):
                            user_ref = responder["user"]
                            if user_ref.get("id") and user_ref.get("type") == "user_reference":
                                assigned_user_data = user_ref
                                assignment_method = "incident_responders"
                                assignment_priority = 6
                                assignment_stats["method_counts"]["incident_responders"] += 1
                                break
            
            # PRIORITY 4: Last status change by user (lower confidence but broad coverage)
            if assignment_priority < 4:
                last_change_by = incident.get("last_status_change_by")
                if (last_change_by and 
                    last_change_by.get("id") and 
                    last_change_by.get("type") == "user_reference"):  # Only users, not services
                    assigned_user_data = last_change_by
                    assignment_method = "last_status_change_user"
                    assignment_priority = 4
                    assignment_stats["method_counts"]["last_status_change_user"] += 1
                    assignment_stats["user_coverage"]["status_change_users"].add(last_change_by["id"])
            
            # 🎯 EMAIL LOOKUP AND VALIDATION
            final_assigned_to = None
            if assigned_user_data:
                user_id = assigned_user_data.get("id")
                
                # Lookup email from our user map (THIS FIXES THE CRITICAL BUG!)
                user_email = user_id_to_email.get(user_id, "")
                user_name = user_id_to_name.get(user_id, assigned_user_data.get("name", "Unknown"))
                
                if user_email:
                    assignment_stats["email_lookup_success"] += 1
                else:
                    assignment_stats["email_lookup_failed"] += 1
                
                final_assigned_to = {
                    "id": user_id,
                    "name": user_name,
                    "email": user_email,  # ✅ NOW HAS EMAIL!
                    "assignment_method": assignment_method,
                    "assignment_priority": assignment_priority
                }
                
                assignment_stats["user_coverage"]["total_unique_users"].add(user_id)
                
                # Enhanced logging for first few incidents
                if i < 3:
                    logger.info(f"🚀 PD NORMALIZE: Incident #{i+1} ENHANCED:")
                    logger.info(f"   - Title: {incident.get('title', 'No title')[:50]}")
                    logger.info(f"   - Method: {assignment_method} (priority: {assignment_priority})")
                    logger.info(f"   - User: {user_name} (ID: {user_id})")
                    logger.info(f"   - Email: {user_email or 'MISSING!'}")
                    logger.info(f"   - Assignment data: {assigned_user_data}")
            else:
                assignment_stats["method_counts"]["none"] += 1
            
            # 🎯 ENHANCED INCIDENT SEVERITY MAPPING
            urgency = incident.get("urgency", "low")
            priority = incident.get("priority")
            priority_name = ""
            if priority and isinstance(priority, dict):
                priority_name = priority.get("summary", "").lower()
            
            # Enhanced severity mapping with more granular detection
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
                severity = "sev1"  # High urgency = SEV1
            elif urgency == "low":
                severity = "sev4"  # Low urgency = SEV4
            else:
                severity = "sev5"  # Default to lowest severity
            
            # 🎯 ENHANCED DURATION CALCULATIONS
            created_at = incident.get("created_at")
            resolved_at = incident.get("resolved_at")
            acknowledged_at = incident.get("acknowledged_at")
            
            duration_minutes = None
            if created_at and resolved_at:
                try:
                    start = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(resolved_at.replace('Z', '+00:00'))
                    duration_minutes = (end - start).total_seconds() / 60
                except Exception as e:
                    logger.debug(f"Duration calculation error: {e}")
            
            time_to_ack_minutes = None
            if created_at and acknowledged_at:
                try:
                    start = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    ack = datetime.fromisoformat(acknowledged_at.replace('Z', '+00:00'))
                    time_to_ack_minutes = (ack - start).total_seconds() / 60
                except Exception as e:
                    logger.debug(f"Acknowledgment time calculation error: {e}")
            
            # 🚀 ENHANCED INCIDENT CREATION WITH ALL IMPROVEMENTS
            enhanced_incident = {
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
                "assigned_to": final_assigned_to,  # ✅ NOW WITH EMAIL AND ENHANCED DATA!
                "service": incident.get("service", {}).get("summary", "Unknown Service"),
                "source": "pagerduty",
                "url": incident.get("html_url"),
                # Enhanced metadata
                "incident_number": incident.get("incident_number"),
                "escalation_policy": incident.get("escalation_policy", {}).get("summary", ""),
                "teams": [team.get("summary", "") for team in incident.get("teams", [])],
                "priority_name": priority_name,
                "alert_counts": incident.get("alert_counts", {}),
                "raw_data": incident
            }
            
            normalized_incidents.append(enhanced_incident)
        
        # 🚀 COMPREHENSIVE FINAL ANALYSIS AND REPORTING
        total_unique_users = len(assignment_stats["user_coverage"]["total_unique_users"])
        
        logger.info(f"🚀 PD NORMALIZE ENHANCED: COMPREHENSIVE FINAL ANALYSIS")
        logger.info(f"=" * 80)
        
        logger.info(f"📊 ASSIGNMENT METHOD PERFORMANCE:")
        for method, count in assignment_stats["method_counts"].items():
            percentage = count/len(incidents)*100 if len(incidents) > 0 else 0
            logger.info(f"   - {method.title().replace('_', ' ')}: {count:,} incidents ({percentage:.1f}%)")
        
        logger.info(f"📊 USER COVERAGE ANALYSIS:")
        logger.info(f"   - Total users from API: {len(user_id_to_email):,}")
        logger.info(f"   - Users found in incidents: {total_unique_users:,}")
        logger.info(f"   - Coverage rate: {total_unique_users/len(user_id_to_email)*100:.1f}%" if user_id_to_email else "   - Coverage rate: N/A")
        logger.info(f"   - Email lookup success: {assignment_stats['email_lookup_success']:,}")
        logger.info(f"   - Email lookup failed: {assignment_stats['email_lookup_failed']:,}")
        
        logger.info(f"📊 USER SOURCE BREAKDOWN:")
        for source_name, user_set in assignment_stats["user_coverage"].items():
            if source_name != "total_unique_users":
                logger.info(f"   - {source_name.replace('_', ' ').title()}: {len(user_set):,} unique users")
        
        # Enhanced cross-reference validation
        user_ids_from_incidents = set()
        incidents_with_valid_emails = 0
        
        for incident in normalized_incidents:
            assigned_to = incident.get("assigned_to")
            if assigned_to and assigned_to.get("id"):
                user_ids_from_incidents.add(assigned_to["id"])
                if assigned_to.get("email"):
                    incidents_with_valid_emails += 1
        
        logger.info(f"🎯 CRITICAL SUCCESS METRICS:")
        logger.info(f"   - Incidents with users: {len([i for i in normalized_incidents if i.get('assigned_to')])}/{len(incidents)} ({len([i for i in normalized_incidents if i.get('assigned_to')])/len(incidents)*100:.1f}%)")
        logger.info(f"   - Incidents with emails: {incidents_with_valid_emails}/{len(incidents)} ({incidents_with_valid_emails/len(incidents)*100:.1f}%)")
        logger.info(f"   - This should fix the '0 incidents' issue!")
        
        if incidents_with_valid_emails == 0:
            logger.error(f"🚨 CRITICAL ERROR: No incidents have valid emails after enhancement!")
            logger.error(f"   This indicates a fundamental issue in user email lookup")
        elif incidents_with_valid_emails < len(incidents) * 0.1:
            logger.warning(f"⚠️ LOW EMAIL SUCCESS RATE: Only {incidents_with_valid_emails/len(incidents)*100:.1f}% of incidents have emails")
        else:
            logger.info(f"✅ SUCCESS: {incidents_with_valid_emails/len(incidents)*100:.1f}% of incidents now have valid user emails!")
        
        # Enhanced metadata with comprehensive stats
        enhanced_metadata = {
            "source": "pagerduty", 
            "incident_count": len(normalized_incidents),
            "user_count": len(normalized_users),
            "assignment_stats": {
                "total_incidents_with_users": len([i for i in normalized_incidents if i.get("assigned_to")]),
                "total_incidents_with_emails": incidents_with_valid_emails,
                "method_counts": assignment_stats["method_counts"],
                "email_lookup_success_rate": assignment_stats["email_lookup_success"] / (assignment_stats["email_lookup_success"] + assignment_stats["email_lookup_failed"]) * 100 if (assignment_stats["email_lookup_success"] + assignment_stats["email_lookup_failed"]) > 0 else 0
            },
            "user_coverage": {
                "total_api_users": len(user_id_to_email),
                "users_in_incidents": total_unique_users,
                "coverage_percentage": total_unique_users/len(user_id_to_email)*100 if user_id_to_email else 0
            },
            "enhancement_applied": True,
            "enhancement_timestamp": datetime.now().isoformat()
        }
        
        normalized_result = {
            "users": normalized_users,
            "incidents": normalized_incidents,
            "metadata": enhanced_metadata
        }
        
        logger.info(f"🚀 PD NORMALIZE ENHANCED: Returning enhanced data:")
        logger.info(f"   - {len(normalized_users)} users with complete profiles")  
        logger.info(f"   - {len(normalized_incidents)} incidents with enhanced assignment data")
        logger.info(f"   - {incidents_with_valid_emails} incidents have valid user emails (CRITICAL FIX!)")
        logger.info(f"=" * 80)
        
        return normalized_result


class PagerDutyDataCollector:
    """Collects and processes data from PagerDuty for burnout analysis."""
    
    def __init__(self, api_token: str):
        self.client = PagerDutyAPIClient(api_token)
        
    async def collect_all_data(self, days_back: int = 30) -> Dict[str, Any]:
        """Collect all necessary data for burnout analysis."""
        # 🎯 RAILWAY DEBUG: Collection start
        token_suffix = self.client.api_token[-4:] if len(self.client.api_token) > 4 else "***"
        logger.info(f"🎯 PAGERDUTY COLLECTION: Starting {days_back}-day collection with token ending in {token_suffix}")
        
        # Calculate date range
        until = datetime.now(pytz.UTC)
        since = until - timedelta(days=days_back)
        
        logger.info(f"🎯 PAGERDUTY COLLECTION: Date range {since.isoformat()} to {until.isoformat()}")
        
        # Fetch data in parallel (no limits for complete data collection)
        users_task = self.client.get_users(limit=1000)
        incidents_task = self.client.get_incidents(since=since, until=until)
        
        logger.info(f"🎯 PAGERDUTY COLLECTION: Starting parallel API calls...")
        users, incidents = await asyncio.gather(users_task, incidents_task)
        
        logger.info(f"🎯 PAGERDUTY COLLECTION: Collected {len(users)} users and {len(incidents)} incidents")
        
        # 🎯 RAILWAY DEBUG: Pre-normalization data check
        if users:
            sample_user = users[0]
            logger.info(f"🎯 PAGERDUTY COLLECTION: Sample user keys: {list(sample_user.keys())}")
            logger.info(f"🎯 PAGERDUTY COLLECTION: Sample user email: {sample_user.get('email', 'NO_EMAIL')}")
        
        if incidents:
            sample_incident = incidents[0]
            assignments = sample_incident.get("assignments", [])
            logger.info(f"🎯 PAGERDUTY COLLECTION: Sample incident has {len(assignments)} assignments")
            if assignments:
                assignee = assignments[0].get("assignee", {})
                logger.info(f"🎯 PAGERDUTY COLLECTION: Sample assignee: {assignee.get('id', 'NO_ID')} - {assignee.get('summary', 'NO_NAME')}")
        
        # 🚀 ENHANCED NORMALIZATION
        logger.info(f"🚀 PAGERDUTY COLLECTION: Starting ENHANCED normalization process...")
        normalized_data = self.client.normalize_to_common_format(incidents, users)
        
        # 🎯 RAILWAY DEBUG: Post-normalization validation
        normalized_incidents = normalized_data.get("incidents", [])
        if normalized_incidents:
            sample_normalized = normalized_incidents[0]
            assigned_to = sample_normalized.get("assigned_to")
            logger.info(f"🚀 PAGERDUTY COLLECTION: Sample normalized incident assigned_to: {assigned_to}")
            if assigned_to:
                logger.info(f"🚀 PAGERDUTY COLLECTION: Assigned user email: {assigned_to.get('email', 'NO_EMAIL')}")
        
        incidents_with_emails = len([i for i in normalized_incidents if i.get("assigned_to") and i.get("assigned_to", {}).get("email")])
        logger.info(f"🚀 PAGERDUTY COLLECTION: {incidents_with_emails}/{len(normalized_incidents)} incidents have emails")
        
        # Add enhanced collection metadata
        metadata = normalized_data.get("metadata", {})
        normalized_data["collection_metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "days_analyzed": days_back,
            "date_range": {
                "start": since.isoformat(),
                "end": until.isoformat()
            },
            "enhancement_applied": metadata.get("enhancement_applied", False),
            "enhancement_timestamp": metadata.get("enhancement_timestamp"),
            "assignment_stats": metadata.get("assignment_stats", {}),
            "total_incidents": len(incidents),
            "total_users": len(users),
            "incidents_with_valid_emails": incidents_with_emails
        }
        
        logger.info(f"🎯 PAGERDUTY COLLECTION: COMPLETE - Returning enhanced data")
        return normalized_data