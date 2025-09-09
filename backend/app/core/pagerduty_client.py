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
        logger.info(f"🎯 PAGERDUTY CLIENT: Enhanced normalization version ACTIVE - Build 875bd95")
        import time
        logger.info(f"🎯 PAGERDUTY CLIENT: On-call methods deployed - Build {int(time.time())}")
        
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
    
    async def get_on_call_shifts(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Get on-call shifts for a specific time period from PagerDuty.
        Returns list of shifts with user information for the exact analysis timeframe.
        """
        try:
            # Format dates for API (PagerDuty expects ISO format with timezone)
            start_str = start_date.astimezone(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end_date.astimezone(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            all_shifts = []
            
            async with aiohttp.ClientSession() as session:
                # Use PagerDuty oncalls API directly - much more efficient
                # This gets all on-call shifts for the time period across all schedules
                logger.info(f"Fetching all on-call shifts for period {start_str} to {end_str}")
                
                oncalls_response = await session.get(
                    f"{self.base_url}/oncalls",
                    headers=self.headers,
                    params={
                        "since": start_str,
                        "until": end_str,
                        "include[]": "users",
                        "limit": 100
                    }
                )
                
                if oncalls_response.status != 200:
                    logger.error(f"Failed to fetch oncalls: {oncalls_response.status} - {await oncalls_response.text()}")
                    return []
                
                oncalls_data = await oncalls_response.json()
                oncalls = oncalls_data.get("oncalls", [])
                
                logger.info(f"Found {len(oncalls)} on-call shifts from PagerDuty")
                
                # Convert PagerDuty oncalls to our shift format
                for oncall in oncalls:
                    shift = {
                        "id": f"pd_{oncall.get('start', '')}_{oncall.get('user', {}).get('id', '')}",
                        "schedule_id": oncall.get("schedule", {}).get("id", ""),
                        "schedule_name": oncall.get("schedule", {}).get("summary", ""),
                        "start_time": oncall.get("start"),
                        "end_time": oncall.get("end"),
                        "user": oncall.get("user", {}),
                        "source": "pagerduty"
                    }
                    all_shifts.append(shift)
                
                logger.info(f"Retrieved {len(all_shifts)} on-call shifts for period {start_str} to {end_str}")
                return all_shifts
                
        except Exception as e:
            logger.error(f"Error fetching on-call shifts: {e}")
            return []
    
    async def extract_on_call_users_from_shifts(self, shifts: List[Dict[str, Any]]) -> set:
        """
        Extract unique user emails from PagerDuty shifts data.
        Returns set of user emails who were on-call during the period.
        """
        if not shifts:
            return set()
        
        on_call_user_emails = set()
        
        for shift in shifts:
            try:
                user = shift.get("user", {})
                email = user.get("email")
                
                if email:
                    on_call_user_emails.add(email.lower().strip())
                    
            except Exception as e:
                logger.warning(f"Error extracting user email from shift: {e}")
                continue
        
        logger.info(f"Successfully extracted {len(on_call_user_emails)} on-call user emails from PagerDuty")
        return on_call_user_emails

    async def collect_analysis_data(self, days_back: int = 30) -> Dict[str, Any]:
        """🚀 ENHANCED: Collect all data needed for burnout analysis with enhanced normalization."""
        # 🎯 CRITICAL FIX: This method was using old normalization - now using enhanced version
        logger.info(f"🚀 ENHANCED PD COLLECT_ANALYSIS_DATA: Starting {days_back}-day collection")
        
        # Delegate to the enhanced data collection method 
        collector = PagerDutyDataCollector(self.api_token)
        enhanced_data = await collector.collect_all_data(days_back)
        
        logger.info(f"🚀 ENHANCED PD COLLECT_ANALYSIS_DATA: Enhanced collection completed")
        return enhanced_data


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
        normalized_data = self._normalize_with_enhanced_assignment_extraction(incidents, users)
        
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
    
    def _normalize_with_enhanced_assignment_extraction(
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
        
        # 🎯 STEP 3: Enhanced incident normalization with multi-source assignment extraction
        logger.info(f"🚀 PD NORMALIZE: Starting ENHANCED incident processing...")
        
        normalized_incidents = []
        assignment_stats = {
            "from_assignments": 0,
            "from_acknowledgments": 0, 
            "from_responders": 0,
            "from_status_changes": 0,
            "no_assignment": 0,
            "assignment_methods": []
        }
        
        incidents_with_emails = 0
        
        for i, incident in enumerate(incidents):
            # 🚀 ENHANCED ASSIGNMENT EXTRACTION with priority system
            assigned_user_info = self._extract_incident_assignment_enhanced(
                incident, user_id_to_email, user_id_to_name
            )
            
            if assigned_user_info:
                method = assigned_user_info.get("assignment_method", "unknown")
                assignment_stats[f"from_{method}"] = assignment_stats.get(f"from_{method}", 0) + 1
                assignment_stats["assignment_methods"].append(method)
                
                if assigned_user_info.get("email"):
                    incidents_with_emails += 1
            else:
                assignment_stats["no_assignment"] += 1
            
            # Create normalized incident
            normalized_incident = {
                "id": incident.get("id"),
                "title": incident.get("title", ""),
                "description": incident.get("description", ""),
                "status": incident.get("status", "open"),
                "severity": self._map_priority_to_severity(incident),
                "created_at": incident.get("created_at"),
                "updated_at": incident.get("last_status_change_at") or incident.get("updated_at"),
                "resolved_at": incident.get("resolved_at") if incident.get("status") == "resolved" else None,
                "assigned_to": assigned_user_info,
                "service": incident.get("service", {}).get("summary", ""),
                "urgency": incident.get("urgency", "low"),
                "source": "pagerduty",
                "raw_data": incident,  # Keep for debugging
                # Enhanced fields
                "incident_number": incident.get("incident_number"),
                "escalation_policy": incident.get("escalation_policy", {}).get("summary", ""),
                "teams": [team.get("summary", "") for team in incident.get("teams", [])],
                "priority_name": incident.get("priority", {}).get("summary", "") if incident.get("priority") else ""
            }
            
            normalized_incidents.append(normalized_incident)
            
            # Log progress for first few incidents
            if i < 3:
                user_email = assigned_user_info.get("email", "None") if assigned_user_info else "None"
                logger.info(f"🚀 PD INCIDENT #{i}: '{normalized_incident['title'][:50]}' -> {user_email}")
        
        # 🎯 STEP 4: Calculate success statistics
        total_incidents = len(incidents)
        assigned_incidents = total_incidents - assignment_stats["no_assignment"]
        
        logger.info(f"🚀 PD NORMALIZE: ASSIGNMENT EXTRACTION RESULTS:")
        logger.info(f"   - Total incidents processed: {total_incidents}")
        logger.info(f"   - Incidents with assignments: {assigned_incidents} ({assigned_incidents/total_incidents*100:.1f}%)")
        logger.info(f"   - Incidents with valid emails: {incidents_with_emails} ({incidents_with_emails/total_incidents*100:.1f}%)")
        logger.info(f"   - Assignment sources:")
        for method, count in assignment_stats.items():
            if method.startswith("from_") and count > 0:
                logger.info(f"     • {method.replace('from_', '').title()}: {count}")
        
        # 🎯 STEP 5: Build final normalized data structure
        normalized_data = {
            "users": normalized_users,
            "incidents": normalized_incidents,
            "total_incidents": total_incidents,
            "total_users": len(users),
            "metadata": {
                "source": "pagerduty",
                "enhancement_applied": True,
                "enhancement_timestamp": datetime.utcnow().isoformat(),
                "assignment_extraction_stats": assignment_stats,
                "email_success_rate": f"{incidents_with_emails}/{total_incidents} ({incidents_with_emails/total_incidents*100:.1f}%)"
            }
        }
        
        logger.info(f"🚀 PD NORMALIZE ENHANCED: COMPLETE!")
        logger.info(f"   - SUCCESS: {incidents_with_emails}/{total_incidents} incidents have user emails")
        
        return normalized_data
    
    def _extract_incident_assignment_enhanced(
        self, 
        incident: Dict[str, Any], 
        user_id_to_email: Dict[str, str],
        user_id_to_name: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        🚀 ENHANCED assignment extraction with multi-source priority system.
        
        Priority order:
        1. Direct assignments (highest confidence)
        2. Acknowledgments (user actively engaged) 
        3. Incident responders (user involved in response)
        4. Status changes (user interacted with incident)
        """
        
        # Priority 1: Direct assignments
        assignments = incident.get("assignments", [])
        if assignments:
            assignee = assignments[0].get("assignee", {})  # Take first assignment
            user_id = assignee.get("id")
            if user_id:
                return {
                    "id": user_id,
                    "name": user_id_to_name.get(user_id, assignee.get("summary", "Unknown")),
                    "email": user_id_to_email.get(user_id, ""),
                    "assignment_method": "assignments",
                    "confidence": "high"
                }
        
        # Priority 2: Acknowledgments
        acknowledgments = incident.get("acknowledgements", []) or incident.get("acknowledgments", [])
        if acknowledgments:
            acknowledger = acknowledgments[0].get("acknowledger", {})  # Take first acknowledgment
            user_id = acknowledger.get("id")
            if user_id and acknowledger.get("type") == "user_reference":
                return {
                    "id": user_id,
                    "name": user_id_to_name.get(user_id, acknowledger.get("summary", "Unknown")),
                    "email": user_id_to_email.get(user_id, ""),
                    "assignment_method": "acknowledgments",
                    "confidence": "medium"
                }
        
        # Priority 3: Incident responders
        responders = incident.get("incidents_responders", [])
        if responders:
            for responder in responders:
                user_ref = responder.get("user")
                if user_ref and user_ref.get("type") == "user_reference":
                    user_id = user_ref.get("id")
                    if user_id:
                        return {
                            "id": user_id,
                            "name": user_id_to_name.get(user_id, user_ref.get("summary", "Unknown")),
                            "email": user_id_to_email.get(user_id, ""),
                            "assignment_method": "responders",
                            "confidence": "medium"
                        }
        
        # Priority 4: Last status change (fallback)
        status_changer = incident.get("last_status_change_by", {})
        if status_changer and status_changer.get("type") == "user_reference":
            user_id = status_changer.get("id")
            if user_id:
                return {
                    "id": user_id,
                    "name": user_id_to_name.get(user_id, status_changer.get("summary", "Unknown")),
                    "email": user_id_to_email.get(user_id, ""),
                    "assignment_method": "status_changes",
                    "confidence": "low"
                }
        
        return None  # No assignment found
    
    def _map_priority_to_severity(self, incident: Dict[str, Any]) -> str:
        """Map PagerDuty priority/urgency to severity level."""
        urgency = incident.get("urgency", "low").lower()
        
        # Check priority first for more specific classification
        priority = incident.get("priority")
        if priority and isinstance(priority, dict):
            priority_name = priority.get("summary", "").lower()
            if not priority_name:
                priority_name = priority.get("name", "").lower()
                
            if "p1" in priority_name or "critical" in priority_name:
                return "sev1"
            elif "p2" in priority_name or "high" in priority_name:
                return "sev2" 
            elif "p3" in priority_name or "medium" in priority_name:
                return "sev3"
            elif "p4" in priority_name or "low" in priority_name:
                return "sev4"
            elif "p5" in priority_name or "info" in priority_name:
                return "sev5"
        
        # Fallback to urgency mapping
        if urgency == "high":
            return "sev1"
        else:
            return "sev4"  # Default for low/unknown urgency